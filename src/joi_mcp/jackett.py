import hashlib
import os
from typing import Annotated, Any, Literal

import httpx
import xmltodict
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from joi_mcp.pagination import DEFAULT_LIMIT, paginate
from joi_mcp.query import apply_query, project
from joi_mcp.schema import optimize_tool_schemas

load_dotenv()

mcp = FastMCP("Jackett")

_client: httpx.Client | None = None
_cache: dict[str, "TorrentDetail"] = {}


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=os.getenv("JACKETT_URL", "http://localhost:9117"),
            timeout=30.0,
        )
    return _client


ID_PREFIX = "jkt_"


def _make_id(guid: str) -> str:
    return ID_PREFIX + hashlib.md5(guid.encode()).hexdigest()[:8]


class TorrentSummary(BaseModel):
    id: str = Field(description="Internal reference ID")
    title: str
    size: int = Field(description="Size in bytes")
    seeders: int = 0
    leechers: int = 0
    indexer: str = ""


class TorrentDetail(BaseModel):
    id: str = Field(description="Internal reference ID")
    title: str
    size: int = Field(description="Size in bytes")
    seeders: int = 0
    leechers: int = 0
    indexer: str = ""
    link: str = Field(description="Download URL")
    magneturl: str | None = Field(default=None, description="Magnet link if available from indexer")
    infohash: str | None = None
    page_url: str = Field(default="", description="Torrent page URL")
    category: list[int] = []
    publish_date: str | None = None


# Keep for backwards compat during transition
TorrentResult = TorrentDetail


class SearchResults(BaseModel):
    results: list[TorrentSummary] | list[dict[str, Any]]
    total: int
    offset: int
    has_more: bool


def _extract_torznab_attrs(attrs: list | dict | None) -> dict:
    """Extract torznab:attr elements into a dict."""
    if attrs is None:
        return {}
    if isinstance(attrs, dict):
        attrs = [attrs]
    result = {}
    for attr in attrs:
        name = attr.get("@name", "")
        value = attr.get("@value", "")
        if name == "seeders":
            result["seeders"] = int(value) if value else 0
        elif name == "peers":
            result["leechers"] = int(value) if value else 0
        elif name == "size":
            result["size"] = int(value) if value else 0
        elif name == "infohash":
            result["infohash"] = value
        elif name == "magneturl":
            result["magneturl"] = value
        elif name == "category":
            result.setdefault("category", []).append(int(value) if value else 0)
        elif name == "tvdbid":
            result["tvdbid"] = value
        elif name == "imdbid":
            result["imdbid"] = value
    return result


def _parse_torznab_response(xml_content: str) -> list[TorrentSummary]:
    """Parse Torznab XML response, cache details, return summaries."""
    data = xmltodict.parse(xml_content)
    channel = data.get("rss", {}).get("channel", {})
    items = channel.get("item", [])

    if isinstance(items, dict):
        items = [items]
    if items is None:
        items = []

    summaries = []
    for item in items:
        attrs = _extract_torznab_attrs(item.get("torznab:attr"))

        # Size can come from torznab:attr or enclosure
        size = attrs.get("size", 0)
        if not size:
            enclosure = item.get("enclosure", {})
            if isinstance(enclosure, dict):
                size = int(enclosure.get("@length", 0) or 0)

        # Get indexer from jackettindexer element or attr
        indexer = ""
        if "jackettindexer" in item:
            indexer_data = item["jackettindexer"]
            if isinstance(indexer_data, dict):
                indexer = indexer_data.get("#text", "")
            else:
                indexer = str(indexer_data) if indexer_data else ""

        guid = item.get("guid", "")
        if isinstance(guid, dict):
            guid = guid.get("#text", "")

        short_id = _make_id(guid)

        detail = TorrentDetail(
            id=short_id,
            title=item.get("title", ""),
            link=item.get("link", ""),
            size=size,
            seeders=attrs.get("seeders", 0),
            leechers=attrs.get("leechers", 0),
            infohash=attrs.get("infohash"),
            magneturl=attrs.get("magneturl"),
            category=attrs.get("category", []),
            indexer=indexer,
            page_url=guid,
            publish_date=item.get("pubDate"),
        )
        _cache[short_id] = detail

        summaries.append(
            TorrentSummary(
                id=short_id,
                title=detail.title,
                size=detail.size,
                seeders=detail.seeders,
                leechers=detail.leechers,
                indexer=detail.indexer,
            )
        )

    return summaries


def _search(params: dict) -> list[TorrentSummary]:
    """Execute search against Jackett API."""
    params["apikey"] = os.getenv("JACKETT_API_KEY", "")
    resp = _get_client().get("/api/v2.0/indexers/all/results/torznab/api", params=params)
    resp.raise_for_status()
    return _parse_torznab_response(resp.text)


@mcp.tool
def search_torrents(
    query: Annotated[str, Field()],
    search_type: Annotated[Literal["search", "movie", "tvsearch"], Field()] = "search",
    year: Annotated[int | None, Field(description="Release year for movie/tvsearch")] = None,
    season: Annotated[int | None, Field(description="Season number for tvsearch")] = None,
    episode: Annotated[int | None, Field(description="Episode number for tvsearch")] = None,
    categories: Annotated[list[int] | None, Field(description="Torznab category IDs (2000=Movies, 5000=TV)")] = None,
    filter_expr: Annotated[str | None, Field(description="JMESPath filter. Examples: seeders > `10`; search(@, 'remux')")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields subset (id auto-included)")] = None,
    sort_by: Annotated[str | None, Field(description="Field to sort by, prefix - for desc (e.g. \"-seeders\")")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
    offset: Annotated[int, Field()] = 0,
) -> SearchResults:
    """Search torrent indexers. Fields: title, size, seeders, leechers, indexer"""
    params = {"t": search_type, "q": query}

    if year:
        params["year"] = str(year)
    if season is not None and search_type == "tvsearch":
        params["season"] = str(season)
    if episode is not None and search_type == "tvsearch":
        params["ep"] = str(episode)
    if categories:
        params["cat"] = ",".join(str(c) for c in categories)

    results = _search(params)
    filtered = apply_query(results, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    projected = project(paginated, fields)
    return SearchResults(results=projected, total=total, offset=offset, has_more=has_more)


@mcp.tool
def get_torrent(
    id: Annotated[str, Field(description="Torrent ID from search results (jkt_xxxxxxxx)")],
) -> TorrentDetail:
    """Get full torrent details including download link by ID."""
    if not id.startswith(ID_PREFIX):
        raise ValueError(f"Invalid torrent ID format: {id}. Expected jkt_xxxxxxxx from search results.")
    if id not in _cache:
        raise ValueError(f"Unknown torrent ID: {id}. Search first.")
    return _cache[id]


optimize_tool_schemas(mcp)
