import pytest
from pydantic import BaseModel

from joi_mcp.query import apply_query


class Item(BaseModel):
    id: int
    name: str
    status: str
    progress: float
    file_count: int = 0


def make_items() -> list[Item]:
    return [
        Item(id=1, name="Ubuntu ISO", status="downloading", progress=50.0, file_count=1),
        Item(id=2, name="Fedora ISO", status="seeding", progress=100.0, file_count=1),
        Item(id=3, name="Debian ISO", status="downloading", progress=75.0, file_count=2),
        Item(id=4, name="Arch Linux", status="stopped", progress=25.0, file_count=0),
    ]


@pytest.mark.unit
class TestApplyQuery:
    def test_no_filters_returns_all(self):
        items = make_items()
        result = apply_query(items)
        assert len(result) == 4
        assert result[0].id == 1

    def test_filter_equality(self):
        items = make_items()
        result = apply_query(items, filter_expr="status=='downloading'")
        assert len(result) == 2
        assert all(i.status == "downloading" for i in result)

    def test_filter_by_id(self):
        items = make_items()
        result = apply_query(items, filter_expr="id==`2`")
        assert len(result) == 1
        assert result[0].name == "Fedora ISO"

    def test_filter_comparison(self):
        items = make_items()
        result = apply_query(items, filter_expr="progress > `50`")
        assert len(result) == 2
        assert all(i.progress > 50 for i in result)

    def test_filter_contains(self):
        items = make_items()
        result = apply_query(items, filter_expr="contains(name, 'ISO')")
        assert len(result) == 3

    def test_filter_file_count(self):
        items = make_items()
        result = apply_query(items, filter_expr="file_count > `1`")
        assert len(result) == 1
        assert result[0].name == "Debian ISO"

    def test_filter_and_logic(self):
        items = make_items()
        result = apply_query(items, filter_expr="status=='downloading' && progress > `60`")
        assert len(result) == 1
        assert result[0].name == "Debian ISO"

    def test_sort_ascending(self):
        items = make_items()
        result = apply_query(items, sort_by="progress")
        assert [i.progress for i in result] == [25.0, 50.0, 75.0, 100.0]

    def test_sort_descending(self):
        items = make_items()
        result = apply_query(items, sort_by="-progress")
        assert [i.progress for i in result] == [100.0, 75.0, 50.0, 25.0]

    def test_limit(self):
        items = make_items()
        result = apply_query(items, limit=2)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

    def test_combined_filter_sort_limit(self):
        items = make_items()
        result = apply_query(items, filter_expr="progress >= `50`", sort_by="-progress", limit=2)
        assert len(result) == 2
        assert result[0].progress == 100.0
        assert result[1].progress == 75.0

    def test_empty_result(self):
        items = make_items()
        result = apply_query(items, filter_expr="status=='nonexistent'")
        assert result == []

    def test_preserves_original_models(self):
        items = make_items()
        result = apply_query(items, filter_expr="id==`1`")
        assert result[0] is items[0]

    def test_raw_jmespath_expression(self):
        items = make_items()
        result = apply_query(items, filter_expr="[?status=='seeding']")
        assert len(result) == 1
        assert result[0].status == "seeding"
