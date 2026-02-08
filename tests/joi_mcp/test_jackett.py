import pytest

from joi_mcp.jackett import get_torrent, search_torrents


@pytest.mark.contract
@pytest.mark.vcr
class TestJackettContract:
    def test_search_torrents_general(self):
        result = search_torrents("ubuntu", limit=5)
        assert result.total >= 0
        if result.results:
            r = result.results[0]
            assert r.title
            assert r.id.startswith("jkt_")  # prefixed hash ID

    def test_search_torrents_movie(self):
        result = search_torrents(
            "matrix",
            search_type="movie",
            year=1999,
            categories=[2000],
            limit=5,
        )
        assert result.total >= 0

    def test_search_torrents_tv(self):
        result = search_torrents(
            "breaking bad",
            search_type="tvsearch",
            season=1,
            episode=1,
            categories=[5000],
            limit=5,
        )
        assert result.total >= 0

    def test_search_with_filter(self):
        result = search_torrents(
            "ubuntu",
            filter_expr="seeders > `0`",
            sort_by="-seeders",
            limit=5,
        )
        if len(result.results) > 1:
            assert result.results[0].seeders >= result.results[1].seeders

    def test_get_torrent_returns_details(self):
        result = search_torrents("ubuntu", limit=1)
        if result.results:
            torrent_id = result.results[0].id
            detail = get_torrent(torrent_id)
            assert detail.id == torrent_id
            assert detail.title == result.results[0].title
            assert detail.link  # has full URL now
