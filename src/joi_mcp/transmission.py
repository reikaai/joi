import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel
from transmission_rpc import Client

from joi_mcp.pagination import DEFAULT_LIMIT, paginate
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


class FolderEntry(BaseModel):
    name: str
    file_count: int
    total_size: int
    completed_size: int
    is_folder: bool = True


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
    total: int
    offset: int
    has_more: bool


class TorrentFileList(BaseModel):
    torrent_id: int
    files: list[TorrentFile | FolderEntry]
    total: int
    offset: int
    has_more: bool
    current_depth: int | None = None
    hint: str | None = None


def _resolve_url(url: str) -> str:
    """Resolve URL, following redirects to magnet links.

    Jackett proxy URLs behave differently per indexer:
    - Some return 302 redirect to magnet: link → extract magnet
    - Some return .torrent file directly → pass URL to transmission

    Transmission can handle both magnet links and torrent file URLs.
    """
    if url.startswith("magnet:"):
        return url
    try:
        resp = httpx.get(url, follow_redirects=False, timeout=10.0)
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if location.startswith("magnet:"):
                return location
    except Exception:
        pass
    return url


def _torrent_to_model(t: Any) -> Torrent:
    file_count = 0
    if hasattr(t, "get_files") and callable(t.get_files):
        try:
            file_count = len(t.get_files())
        except KeyError:
            pass  # Files not fetched yet (e.g. newly added torrent)
    return Torrent(
        id=t.id,
        name=t.name,
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        progress=t.progress,
        eta=int(t.eta.total_seconds()) if t.eta is not None and t.eta.total_seconds() >= 0 else None,
        total_size=t.total_size,
        comment=t.comment or "",
        error_string=t.error_string or "",
        download_speed=t.rate_download,
        upload_speed=t.rate_upload,
        file_count=file_count,
    )


def _aggregate_by_depth(files: list[TorrentFile], depth: int) -> list[TorrentFile | FolderEntry]:
    """Aggregate files into folders up to given depth."""
    if depth < 1:
        return list(files)

    folders: dict[str, FolderEntry] = {}
    result: list[TorrentFile | FolderEntry] = []

    for f in files:
        parts = f.name.split("/")
        if len(parts) <= depth:
            result.append(f)
        else:
            folder_path = "/".join(parts[:depth])
            if folder_path not in folders:
                folders[folder_path] = FolderEntry(
                    name=folder_path,
                    file_count=0,
                    total_size=0,
                    completed_size=0,
                )
            folders[folder_path].file_count += 1
            folders[folder_path].total_size += f.size
            folders[folder_path].completed_size += f.completed

    return result + list(folders.values())


@mcp.tool
def list_torrents(
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> TorrentList:
    """List torrents with pagination.

    Args:
        filter_expr: JMESPath filter (e.g. "status=='downloading'", "id==`42`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-progress")
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    torrents = get_client().get_torrents()
    items = [_torrent_to_model(t) for t in torrents]
    filtered = apply_query(items, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return TorrentList(torrents=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def search_torrents(
    query: str,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> TorrentList:
    """Search LOCAL download queue by name. Use to find ALREADY ADDED torrents.

    Args:
        query: Search string for name matching
        filter_expr: JMESPath filter (e.g. "status=='downloading'", "progress > `50`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-progress")
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    torrents = get_client().get_torrents()
    query_lower = query.lower()
    matched = [t for t in torrents if query_lower in t.name.lower()]
    items = [_torrent_to_model(t) for t in matched]
    filtered = apply_query(items, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return TorrentList(torrents=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def add_torrent(url: str, download_dir: str | None = None) -> Torrent:
    """Add a torrent by URL or magnet link"""
    client = get_client()
    resolved_url = _resolve_url(url)
    t = client.add_torrent(resolved_url, download_dir=download_dir)
    full_torrent = client.get_torrent(t.id)
    return _torrent_to_model(full_torrent)


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
    depth: int | None = 1,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> TorrentFileList:
    """List files/folders in a torrent with hierarchical browsing.

    **Workflow for TV shows/multi-folder torrents:**
    1. Call with depth=1 (default) → see top-level folders
    2. Call with depth=2 → see subfolders (e.g., seasons)
    3. Call with depth=3+ or depth=None → see actual files

    **Example for "Scrubs" with 9 seasons:**
    - depth=1: Returns [FolderEntry("Scrubs", file_count=182)]
    - depth=2: Returns [FolderEntry("Scrubs/Season 1"), FolderEntry("Scrubs/Season 2"), ...]
    - depth=3 or None: Returns actual episode files

    Args:
        torrent_id: Torrent ID
        depth: Folder depth. 1=top-level (default), 2=two levels, 3+=deeper, None=all files flat
        filter_expr: JMESPath filter (e.g. "contains(name, 'S01')")
        sort_by: Field to sort by (e.g. "-size", "name")
        limit: Max results per page (default 50)
        offset: Pagination offset (default 0)
    """
    rpc_torrent = get_client().get_torrent(torrent_id)
    files = []
    for i, f in enumerate(rpc_torrent.get_files()):
        prio = f.priority.value if hasattr(f.priority, "value") else (f.priority or 1)
        files.append(TorrentFile(index=i, name=f.name, size=f.size, completed=f.completed, priority=prio))

    entries = _aggregate_by_depth(files, depth) if depth else files
    filtered = apply_query(entries, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)

    hint = None
    if depth is not None:
        has_folders = any(isinstance(e, FolderEntry) for e in paginated)
        if has_folders:
            hint = f"Folders found. To see their contents, increase depth (e.g., depth={depth + 1}) or use depth=None for all files."

    return TorrentFileList(
        torrent_id=torrent_id,
        files=paginated,
        total=total,
        offset=offset,
        has_more=has_more,
        current_depth=depth,
        hint=hint,
    )


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
