import pytest
from transmission_rpc.error import TransmissionError

import joi_mcp.transmission as tm
from joi_mcp.transmission import (
    get_torrent,
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
        # Search for something - may or may not have matches
        result = search_torrents("test")
        assert hasattr(result, "torrents")
        assert isinstance(result.torrents, list)

    def test_search_torrents_no_match(self):
        result = search_torrents("xyznonexistent123456789")
        assert result.torrents == []

    def test_get_torrent_from_list(self):
        all_torrents = list_torrents()
        if not all_torrents.torrents:
            pytest.skip("No torrents available for testing")

        torrent_id = all_torrents.torrents[0].id
        result = get_torrent(torrent_id)
        assert result.id == torrent_id
        assert result.name is not None
