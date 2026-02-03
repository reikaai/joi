import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel
from transmission_rpc import Client

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


class Torrent(BaseModel):
    id: int
    name: str
    status: str
    progress: float
    download_speed: int
    upload_speed: int
    eta: int | None
    total_size: int
    comment: str
    error_string: str


class TorrentList(BaseModel):
    torrents: list[Torrent]


def _torrent_to_model(t) -> Torrent:
    return Torrent(
        id=t.id,
        name=t.name,
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        progress=t.progress,
        download_speed=t.rate_download,
        upload_speed=t.rate_upload,
        eta=t.eta if t.eta and t.eta >= 0 else None,
        total_size=t.total_size,
        comment=t.comment or "",
        error_string=t.error_string or "",
    )


@mcp.tool
def list_torrents() -> TorrentList:
    """List all torrents"""
    torrents = get_client().get_torrents()
    return TorrentList(torrents=[_torrent_to_model(t) for t in torrents])


@mcp.tool
def search_torrents(query: str) -> TorrentList:
    """Search torrents by name (case-insensitive substring match)"""
    torrents = get_client().get_torrents()
    query_lower = query.lower()
    matched = [t for t in torrents if query_lower in t.name.lower()]
    return TorrentList(torrents=[_torrent_to_model(t) for t in matched])


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
def get_torrent(torrent_id: int) -> Torrent:
    """Get details of a specific torrent"""
    t = get_client().get_torrent(torrent_id)
    return _torrent_to_model(t)
