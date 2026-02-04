import pytest

from joi_mcp.pagination import DEFAULT_LIMIT, paginate


@pytest.mark.unit
class TestPaginate:
    def test_default_limit(self):
        assert DEFAULT_LIMIT == 50

    def test_returns_all_when_under_limit(self):
        items = list(range(10))
        paginated, total, has_more = paginate(items)
        assert paginated == items
        assert total == 10
        assert has_more is False

    def test_returns_limited_items(self):
        items = list(range(100))
        paginated, total, has_more = paginate(items, limit=10)
        assert paginated == list(range(10))
        assert total == 100
        assert has_more is True

    def test_offset_skips_items(self):
        items = list(range(100))
        paginated, total, has_more = paginate(items, limit=10, offset=50)
        assert paginated == list(range(50, 60))
        assert total == 100
        assert has_more is True

    def test_last_page_has_more_false(self):
        items = list(range(25))
        paginated, total, has_more = paginate(items, limit=10, offset=20)
        assert paginated == [20, 21, 22, 23, 24]
        assert total == 25
        assert has_more is False

    def test_offset_beyond_length_returns_empty(self):
        items = list(range(10))
        paginated, total, has_more = paginate(items, limit=10, offset=100)
        assert paginated == []
        assert total == 10
        assert has_more is False

    def test_empty_list(self):
        paginated, total, has_more = paginate([])
        assert paginated == []
        assert total == 0
        assert has_more is False

    def test_exact_boundary(self):
        items = list(range(50))
        paginated, total, has_more = paginate(items, limit=50, offset=0)
        assert len(paginated) == 50
        assert has_more is False
