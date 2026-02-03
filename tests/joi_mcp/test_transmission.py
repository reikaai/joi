import pytest
from transmission_rpc.error import TransmissionError

import joi_mcp.transmission as tm
from joi_mcp.transmission import (
    list_torrents,
    search_torrents,
)


def _check_transmission_available():
    """Check if Transmission daemon is reachable."""
    try:
        tm._client = None  # Reset singleton
        tm.get_client()
        return True
    except (TransmissionError, OSError, ConnectionError):
        return False
    finally:
        tm._client = None


requires_transmission = pytest.mark.skipif(
    not _check_transmission_available(),
    reason="Transmission daemon not available",
)


@pytest.mark.contract
@pytest.mark.vcr
@requires_transmission
class TestTransmissionContract:
    def test_list_torrents(self):
        result = list_torrents()
        assert hasattr(result, "torrents")
        assert isinstance(result.torrents, list)

    def test_search_torrents(self):
        result = search_torrents("test")
        assert hasattr(result, "torrents")
        assert isinstance(result.torrents, list)

    def test_search_torrents_no_match(self):
        result = search_torrents("xyznonexistent123456789")
        assert result.torrents == []

    def test_list_torrents_with_filter(self):
        result = list_torrents(filter_expr="progress >= `0`")
        assert hasattr(result, "torrents")
        assert isinstance(result.torrents, list)

    def test_list_torrents_with_sort(self):
        result = list_torrents(sort_by="-progress")
        assert hasattr(result, "torrents")
        if len(result.torrents) > 1:
            assert result.torrents[0].progress >= result.torrents[1].progress

    def test_list_torrents_with_limit(self):
        result = list_torrents(limit=1)
        assert len(result.torrents) <= 1

    def test_list_torrents_filter_by_id(self):
        all_torrents = list_torrents()
        if not all_torrents.torrents:
            pytest.skip("No torrents available for testing")

        torrent_id = all_torrents.torrents[0].id
        result = list_torrents(filter_expr=f"id==`{torrent_id}`")
        assert len(result.torrents) == 1
        assert result.torrents[0].id == torrent_id
