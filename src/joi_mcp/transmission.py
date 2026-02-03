import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel
from transmission_rpc import Client

from joi_mcp.query import apply_query

load_dotenv()

mcp = FastMCP("Transmission")

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        protocol = "https" if os.getenv("TRANSMISSION_SSL", "").lower() in ("1", "true") else "http"
        _client = Client(
            protocol=protocol,
            host=os.getenv("TRANSMISSION_HOST", "localhost"),
            port=int(os.getenv("TRANSMISSION_PORT", "9091")),
            path=os.getenv("TRANSMISSION_PATH", "/transmission/rpc"),
            username=os.getenv("TRANSMISSION_USER") or None,
            password=os.getenv("TRANSMISSION_PASS") or None,
        )
    return _client


class TorrentFile(BaseModel):
    index: int
    name: str
    size: int
    completed: int
    priority: int


class Torrent(BaseModel):
    id: int
    name: str
    status: str
    progress: float
    eta: int | None
    total_size: int
    comment: str
    error_string: str
    download_speed: int
    upload_speed: int
    file_count: int


class TorrentList(BaseModel):
    torrents: list[Torrent]


class TorrentFileList(BaseModel):
    torrent_id: int
    files: list[TorrentFile]


def _torrent_to_model(t: Any) -> Torrent:
    file_count = 0
    if hasattr(t, "files") and t.files:
        file_count = len(t.files())
    return Torrent(
        id=t.id,
        name=t.name,
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        progress=t.progress,
        eta=t.eta if t.eta and t.eta >= 0 else None,
        total_size=t.total_size,
        comment=t.comment or "",
        error_string=t.error_string or "",
        download_speed=t.rate_download,
        upload_speed=t.rate_upload,
        file_count=file_count,
    )


@mcp.tool
def list_torrents(
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> TorrentList:
    """List torrents with JMESPath query support.

    Args:
        filter_expr: JMESPath filter (e.g. "status=='downloading'", "id==`42`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-progress")
        limit: Max results
    """
    torrents = get_client().get_torrents()
    items = [_torrent_to_model(t) for t in torrents]
    filtered = apply_query(items, filter_expr, sort_by, limit)
    return TorrentList(torrents=filtered)


@mcp.tool
def search_torrents(
    query: str,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> TorrentList:
    """Search torrents by name (case-insensitive substring match) with JMESPath query support.

    Args:
        query: Search string for name matching
        filter_expr: JMESPath filter (e.g. "status=='downloading'", "progress > `50`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-progress")
        limit: Max results
    """
    torrents = get_client().get_torrents()
    query_lower = query.lower()
    matched = [t for t in torrents if query_lower in t.name.lower()]
    items = [_torrent_to_model(t) for t in matched]
    filtered = apply_query(items, filter_expr, sort_by, limit)
    return TorrentList(torrents=filtered)


@mcp.tool
def add_torrent(url: str, download_dir: str | None = None) -> Torrent:
    """Add a torrent by URL or magnet link"""
    t = get_client().add_torrent(url, download_dir=download_dir)
    return _torrent_to_model(t)


@mcp.tool
def remove_torrent(torrent_id: int, delete_data: bool = False) -> bool:
    """Remove a torrent, optionally deleting downloaded data"""
    get_client().remove_torrent(torrent_id, delete_data=delete_data)
    return True


@mcp.tool
def pause_torrent(torrent_id: int) -> bool:
    """Pause a torrent"""
    get_client().stop_torrent(torrent_id)
    return True


@mcp.tool
def resume_torrent(torrent_id: int) -> bool:
    """Resume a paused torrent"""
    get_client().start_torrent(torrent_id)
    return True


@mcp.tool
def list_files(
    torrent_id: int,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> TorrentFileList:
    """List files in a torrent with JMESPath query support.

    Args:
        torrent_id: Torrent ID
        filter_expr: JMESPath filter (e.g. "contains(name, 'S01')")
        sort_by: Field to sort by (e.g. "-size")
        limit: Max results
    """
    rpc_torrent = get_client().get_torrent(torrent_id)
    files = [
        TorrentFile(index=i, name=f.name, size=f.size, completed=f.completed, priority=f.priority)
        for i, f in enumerate(rpc_torrent.files())  # type: ignore[attr-defined]
    ]
    filtered = apply_query(files, filter_expr, sort_by, limit)
    return TorrentFileList(torrent_id=torrent_id, files=filtered)


@mcp.tool
def set_file_priorities(
    torrent_id: int,
    file_indices: list[int],
    priority: int,
) -> bool:
    """Set download priority for specific files.

    Args:
        torrent_id: Torrent ID
        file_indices: List of file indices (0-based, from list_torrent_files)
        priority: 0=skip, 1=low, 2=normal, 3=high
    """
    client = get_client()
    if priority == 0:
        client.change_torrent(torrent_id, files_unwanted=file_indices)
    else:
        client.change_torrent(torrent_id, files_wanted=file_indices)
        if priority == 1:
            client.change_torrent(torrent_id, priority_low=file_indices)
        elif priority == 2:
            client.change_torrent(torrent_id, priority_normal=file_indices)
        elif priority == 3:
            client.change_torrent(torrent_id, priority_high=file_indices)
    return True
