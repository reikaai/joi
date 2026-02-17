import pytest
from pydantic import BaseModel

from joi_mcp.query import apply_query, project


class Item(BaseModel):
    id: int
    name: str
    status: str
    progress: float
    file_count: int = 0
    comment: str = ""


def make_items() -> list[Item]:
    return [
        Item(id=1, name="Ubuntu ISO", status="downloading", progress=50.0, file_count=1),
        Item(id=2, name="Fedora ISO", status="seeding", progress=100.0, file_count=1),
        Item(id=3, name="Debian ISO", status="downloading", progress=75.0, file_count=2),
        Item(id=4, name="Arch Linux", status="stopped", progress=25.0, file_count=0),
    ]


def make_items_with_comments() -> list[Item]:
    return [
        Item(id=1, name="The Matrix", status="seeding", progress=100.0, comment="1999 Sci-Fi"),
        Item(id=2, name="Interstellar", status="seeding", progress=100.0, comment="Nolan film"),
        Item(id=3, name="MATRIX Reloaded", status="downloading", progress=50.0, comment="Sequel"),
        Item(id=4, name="Inception", status="seeding", progress=100.0, comment="nolan masterpiece"),
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
        assert all(r.status == "downloading" for r in result)

    def test_filter_by_id(self):
        items = make_items()
        result = apply_query(items, filter_expr="id==`2`")
        assert len(result) == 1
        assert result[0].name == "Fedora ISO"

    def test_filter_comparison(self):
        items = make_items()
        result = apply_query(items, filter_expr="progress > `50`")
        assert len(result) == 2
        assert all(r.progress > 50 for r in result)

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
        assert [r.progress for r in result] == [25.0, 50.0, 75.0, 100.0]

    def test_sort_descending(self):
        items = make_items()
        result = apply_query(items, sort_by="-progress")
        assert [r.progress for r in result] == [100.0, 75.0, 50.0, 25.0]

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

    def test_returns_models(self):
        items = make_items()
        result = apply_query(items, filter_expr="id==`1`")
        assert isinstance(result[0], Item)
        assert result[0].id == 1
        assert result[0].name == "Ubuntu ISO"

    def test_raw_jmespath_expression(self):
        items = make_items()
        result = apply_query(items, filter_expr="[?status=='seeding']")
        assert len(result) == 1
        assert result[0].status == "seeding"

    def test_empty_list(self):
        result = apply_query([])
        assert result == []


@pytest.mark.unit
class TestSearchFunction:
    def test_search_case_insensitive(self):
        items = make_items_with_comments()
        result = apply_query(items, filter_expr="search(@, 'matrix')")
        assert len(result) == 2
        assert {r.name for r in result} == {"The Matrix", "MATRIX Reloaded"}

    def test_search_in_comment(self):
        items = make_items_with_comments()
        result = apply_query(items, filter_expr="search(@, 'nolan')")
        assert len(result) == 2
        assert {r.name for r in result} == {"Interstellar", "Inception"}

    def test_search_with_progress_filter(self):
        items = make_items_with_comments()
        result = apply_query(items, filter_expr="search(@, 'matrix') && progress >= `100`")
        assert len(result) == 1
        assert result[0].name == "The Matrix"

    def test_search_no_match(self):
        items = make_items_with_comments()
        result = apply_query(items, filter_expr="search(@, 'nonexistent')")
        assert result == []

    def test_search_with_sort(self):
        items = make_items_with_comments()
        result = apply_query(items, filter_expr="search(@, 'matrix')", sort_by="progress")
        assert len(result) == 2
        assert result[0].progress == 50.0
        assert result[1].progress == 100.0


@pytest.mark.unit
class TestProject:
    def test_project_single_field(self):
        items = make_items()
        result = project(items, fields=["name"])
        assert len(result) == 4
        assert set(result[0].keys()) == {"id", "name"}

    def test_project_multiple_fields(self):
        items = make_items()
        result = project(items, fields=["name", "progress"])
        assert len(result) == 4
        assert set(result[0].keys()) == {"id", "name", "progress"}

    def test_id_always_included(self):
        items = make_items()
        result = project(items, fields=["status"])
        assert "id" in result[0]

    def test_no_fields_returns_models(self):
        items = make_items()
        result = project(items, fields=None)
        assert result is items
        assert isinstance(result[0], Item)

    def test_empty_list(self):
        result = project([], fields=["name"])
        assert result == []

    def test_project_after_filter(self):
        items = make_items()
        filtered = apply_query(items, filter_expr="status=='seeding'")
        result = project(filtered, fields=["name"])
        assert len(result) == 1
        assert set(result[0].keys()) == {"id", "name"}
        assert result[0]["name"] == "Fedora ISO"

    def test_project_after_sort(self):
        items = make_items()
        sorted_items = apply_query(items, sort_by="-progress")
        result = project(sorted_items, fields=["name", "progress"])
        assert result[0]["progress"] == 100.0
        assert set(result[0].keys()) == {"id", "name", "progress"}

    def test_project_after_limit(self):
        items = make_items()
        limited = apply_query(items, limit=2)
        result = project(limited, fields=["name"])
        assert len(result) == 2
        assert set(result[0].keys()) == {"id", "name"}

    def test_project_combined_pipeline(self):
        items = make_items()
        filtered = apply_query(items, filter_expr="progress >= `50`", sort_by="-progress", limit=2)
        result = project(filtered, fields=["name", "progress"])
        assert len(result) == 2
        assert result[0]["progress"] == 100.0
        assert set(result[0].keys()) == {"id", "name", "progress"}


@pytest.mark.unit
class TestSearchNormalized:
    """search() matches across transliteration, Cyrillic, dot-separated titles."""

    def _items(self):
        return [
            Item(id=1, name="Интерстеллар 2014 BDRip 1080p", status="ok", progress=0),
            Item(id=2, name="I.n.t.e.r.s.t.e.l.l.a.r.2014", status="ok", progress=0),
            Item(id=3, name="Interstellar (2014)", status="ok", progress=0),
            Item(id=4, name="Unrelated Movie", status="ok", progress=0),
        ]

    def test_english_matches_cyrillic(self):
        result = apply_query(self._items(), filter_expr="search(@, 'interstellar')")
        ids = {r.id for r in result}
        assert ids == {1, 2, 3}

    def test_cyrillic_needle_matches_cyrillic(self):
        result = apply_query(self._items(), filter_expr="search(@, 'Интерстеллар')")
        ids = {r.id for r in result}
        assert 1 in ids

    def test_dot_separated_matches(self):
        result = apply_query(self._items(), filter_expr="search(@, 'interstellar')")
        ids = {r.id for r in result}
        assert 2 in ids

    def test_no_false_positives(self):
        result = apply_query(self._items(), filter_expr="search(@, 'inception')")
        assert result == []


@pytest.mark.unit
class TestIndexKeyField:
    class FileItem(BaseModel):
        index: int
        name: str
        size: int

    def test_apply_query_returns_models(self):
        items = [
            self.FileItem(index=0, name="file1.txt", size=100),
            self.FileItem(index=1, name="file2.txt", size=200),
        ]
        result = apply_query(items)
        assert isinstance(result[0], self.FileItem)
        assert result[0].index == 0

    def test_project_uses_index_as_key(self):
        items = [
            self.FileItem(index=0, name="file1.txt", size=100),
            self.FileItem(index=1, name="file2.txt", size=200),
        ]
        result = project(items, fields=["name"])
        assert set(result[0].keys()) == {"index", "name"}

    def test_index_always_included(self):
        items = [
            self.FileItem(index=0, name="file1.txt", size=100),
        ]
        result = project(items, fields=["size"])
        assert "index" in result[0]
