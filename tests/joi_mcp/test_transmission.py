import pytest
from transmission_rpc.error import TransmissionError

import joi_mcp.transmission as tm
from joi_mcp.transmission import list_torrents


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


def _parse_tsv_rows(result) -> list[dict[str, str]]:
    """Parse TsvList.data into list of dicts keyed by header."""
    lines = result.data.strip().split("\n")
    if not lines:
        return []
    headers = lines[0].split("\t")
    return [{h: v for h, v in zip(headers, row.split("\t"))} for row in lines[1:]]


@pytest.mark.contract
@pytest.mark.vcr
@requires_transmission
class TestTransmissionContract:
    def test_list_torrents(self):
        result = list_torrents()
        assert hasattr(result, "data")
        assert result.total > 0
        rows = _parse_tsv_rows(result)
        assert len(rows) > 0
        assert "id" in rows[0]
        assert "name" in rows[0]

    def test_list_torrents_with_search(self):
        result = list_torrents(filter_expr="search(@, 'xyznonexistent123456789')")
        rows = _parse_tsv_rows(result)
        assert rows == []

    def test_list_torrents_with_filter(self):
        result = list_torrents(filter_expr="progress >= `0`")
        assert result.total > 0
        rows = _parse_tsv_rows(result)
        assert len(rows) > 0

    def test_list_torrents_with_sort(self):
        result = list_torrents(sort_by="-progress")
        rows = _parse_tsv_rows(result)
        if len(rows) > 1:
            assert float(rows[0]["progress"]) >= float(rows[1]["progress"])

    def test_list_torrents_with_limit(self):
        result = list_torrents(limit=1)
        rows = _parse_tsv_rows(result)
        assert len(rows) <= 1

    def test_list_torrents_filter_by_id(self):
        all_result = list_torrents()
        rows = _parse_tsv_rows(all_result)
        if not rows:
            pytest.skip("No torrents available for testing")

        torrent_id = rows[0]["id"]
        result = list_torrents(filter_expr=f"id==`{torrent_id}`")
        filtered_rows = _parse_tsv_rows(result)
        assert len(filtered_rows) == 1
        assert filtered_rows[0]["id"] == torrent_id
