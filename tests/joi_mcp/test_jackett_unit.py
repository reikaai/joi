import pytest

from joi_mcp.jackett import (
    SearchResults,
    TorrentDetail,
    TorrentSummary,
    _cache,
    _extract_torznab_attrs,
    _make_id,
    _parse_torznab_response,
    get_torrent,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <title>Jackett</title>
    <item>
      <title>Ubuntu 24.04 LTS</title>
      <guid>https://example.com/torrent/123</guid>
      <link>https://example.com/download/123.torrent</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
      <jackettindexer id="example">ExampleTracker</jackettindexer>
      <torznab:attr name="seeders" value="100"/>
      <torznab:attr name="peers" value="50"/>
      <torznab:attr name="size" value="4294967296"/>
      <torznab:attr name="infohash" value="abc123def456"/>
      <torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc123def456"/>
      <torznab:attr name="category" value="2000"/>
      <torznab:attr name="category" value="2010"/>
    </item>
  </channel>
</rss>"""

SINGLE_ITEM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>Single Result</title>
      <guid>single-guid</guid>
      <link>https://example.com/single.torrent</link>
      <torznab:attr name="seeders" value="5"/>
    </item>
  </channel>
</rss>"""

EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <title>Jackett</title>
  </channel>
</rss>"""

ENCLOSURE_SIZE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <item>
      <title>Enclosure Size Test</title>
      <guid>enc-guid</guid>
      <link>https://example.com/enc.torrent</link>
      <enclosure url="https://example.com/enc.torrent" length="1073741824" type="application/x-bittorrent"/>
      <torznab:attr name="seeders" value="10"/>
    </item>
  </channel>
</rss>"""


@pytest.mark.unit
class TestModels:
    def test_torrent_summary_model(self):
        data = {
            "id": "a1b2c3d4",
            "title": "Test Torrent",
            "size": 1073741824,
            "seeders": 50,
            "leechers": 10,
            "indexer": "ExampleTracker",
        }
        result = TorrentSummary.model_validate(data)
        assert result.id == "a1b2c3d4"
        assert result.title == "Test Torrent"
        assert result.size == 1073741824
        assert result.seeders == 50
        assert result.leechers == 10
        assert result.indexer == "ExampleTracker"

    def test_torrent_summary_defaults(self):
        data = {"id": "abc", "title": "Minimal", "size": 0}
        result = TorrentSummary.model_validate(data)
        assert result.seeders == 0
        assert result.leechers == 0
        assert result.indexer == ""

    def test_torrent_detail_model(self):
        data = {
            "id": "a1b2c3d4",
            "title": "Test Torrent",
            "link": "https://example.com/download.torrent",
            "size": 1073741824,
            "seeders": 50,
            "leechers": 10,
            "infohash": "abc123",
            "magneturl": "magnet:?xt=urn:btih:abc123",
            "category": [2000, 2010],
            "indexer": "ExampleTracker",
            "page_url": "https://example.com/torrent/123",
            "publish_date": "2024-01-01T00:00:00Z",
        }
        result = TorrentDetail.model_validate(data)
        assert result.id == "a1b2c3d4"
        assert result.title == "Test Torrent"
        assert result.size == 1073741824
        assert result.link == "https://example.com/download.torrent"
        assert result.infohash == "abc123"
        assert result.category == [2000, 2010]
        assert result.page_url == "https://example.com/torrent/123"

    def test_torrent_detail_defaults(self):
        data = {"id": "abc", "title": "Minimal", "link": "https://example.com", "size": 0}
        result = TorrentDetail.model_validate(data)
        assert result.seeders == 0
        assert result.magneturl is None
        assert result.infohash is None
        assert result.category == []
        assert result.page_url == ""
        assert result.publish_date is None

    def test_search_results_model(self):
        data = {
            "results": [
                {"id": "a1", "title": "Result 1", "size": 100},
                {"id": "b2", "title": "Result 2", "size": 200},
            ],
            "total": 10,
            "offset": 0,
            "has_more": True,
        }
        sr = SearchResults.model_validate(data)
        assert len(sr.results) == 2
        assert sr.total == 10
        assert sr.has_more is True


@pytest.mark.unit
class TestMakeId:
    def test_returns_prefixed_hash(self):
        result = _make_id("https://example.com/torrent/123")
        assert result.startswith("jkt_")
        assert len(result) == 12  # "jkt_" + 8 hex chars

    def test_deterministic(self):
        guid = "https://example.com/torrent/456"
        assert _make_id(guid) == _make_id(guid)

    def test_different_guids_different_ids(self):
        id1 = _make_id("https://example.com/torrent/1")
        id2 = _make_id("https://example.com/torrent/2")
        assert id1 != id2


@pytest.mark.unit
class TestExtractTorznabAttrs:
    def test_extracts_single_attr_as_dict(self):
        attrs = {"@name": "seeders", "@value": "100"}
        result = _extract_torznab_attrs(attrs)
        assert result["seeders"] == 100

    def test_extracts_multiple_attrs(self):
        attrs = [
            {"@name": "seeders", "@value": "100"},
            {"@name": "peers", "@value": "50"},
            {"@name": "size", "@value": "1024"},
        ]
        result = _extract_torznab_attrs(attrs)
        assert result["seeders"] == 100
        assert result["leechers"] == 50
        assert result["size"] == 1024

    def test_handles_multiple_categories(self):
        attrs = [
            {"@name": "category", "@value": "2000"},
            {"@name": "category", "@value": "2010"},
        ]
        result = _extract_torznab_attrs(attrs)
        assert result["category"] == [2000, 2010]

    def test_handles_none_attrs(self):
        result = _extract_torznab_attrs(None)
        assert result == {}

    def test_handles_empty_values(self):
        attrs = [{"@name": "seeders", "@value": ""}]
        result = _extract_torznab_attrs(attrs)
        assert result["seeders"] == 0


@pytest.mark.unit
class TestParseTorznabResponse:
    def test_parses_full_response(self):
        _cache.clear()
        summaries = _parse_torznab_response(SAMPLE_XML)
        assert len(summaries) == 1
        s = summaries[0]
        assert s.title == "Ubuntu 24.04 LTS"
        assert s.id.startswith("jkt_")
        assert len(s.id) == 12
        assert s.seeders == 100
        assert s.leechers == 50
        assert s.size == 4294967296
        assert s.indexer == "ExampleTracker"
        # Check cache has full details
        detail = _cache[s.id]
        assert detail.link == "https://example.com/download/123.torrent"
        assert detail.infohash == "abc123def456"
        assert "magnet:" in detail.magneturl
        assert detail.category == [2000, 2010]
        assert detail.page_url == "https://example.com/torrent/123"

    def test_handles_single_item(self):
        _cache.clear()
        summaries = _parse_torznab_response(SINGLE_ITEM_XML)
        assert len(summaries) == 1
        assert summaries[0].title == "Single Result"
        assert summaries[0].seeders == 5
        assert summaries[0].id in _cache

    def test_handles_empty_response(self):
        _cache.clear()
        summaries = _parse_torznab_response(EMPTY_XML)
        assert summaries == []

    def test_uses_enclosure_size_as_fallback(self):
        _cache.clear()
        summaries = _parse_torznab_response(ENCLOSURE_SIZE_XML)
        assert len(summaries) == 1
        assert summaries[0].size == 1073741824


@pytest.mark.unit
class TestGetTorrent:
    def test_returns_cached_detail(self):
        _cache.clear()
        _parse_torznab_response(SAMPLE_XML)
        # Get the ID from cache
        torrent_id = list(_cache.keys())[0]
        detail = get_torrent(torrent_id)
        assert detail.title == "Ubuntu 24.04 LTS"
        assert detail.link == "https://example.com/download/123.torrent"

    def test_raises_for_unknown_id(self):
        _cache.clear()
        with pytest.raises(ValueError, match="Invalid torrent ID format"):
            get_torrent("nonexistent")
