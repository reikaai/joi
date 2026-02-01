import pytest

from joi_mcp.tmdb import (
    find_by_name,
    get_recommendations,
    get_similar,
    list_by_genre,
    list_genres,
    lookup_by_imdb,
)


@pytest.mark.contract
@pytest.mark.vcr
class TestTMDBContract:
    def test_find_by_name(self):
        result = find_by_name("The Matrix", year=1999)
        assert len(result.movies) > 0
        assert "Matrix" in result.movies[0].title

    def test_lookup_by_imdb_movie(self):
        result = lookup_by_imdb("tt0133093")  # The Matrix
        assert len(result.movie_results) == 1
        assert result.movie_results[0].title == "The Matrix"

    def test_lookup_by_imdb_tv(self):
        result = lookup_by_imdb("tt0903747")  # Breaking Bad
        assert len(result.tv_results) == 1
        assert result.tv_results[0].name == "Breaking Bad"

    def test_get_recommendations(self):
        result = get_recommendations(603)  # The Matrix
        assert len(result.movies) > 0

    def test_get_similar(self):
        result = get_similar(603)
        assert len(result.movies) > 0

    def test_list_by_genre(self):
        result = list_by_genre(28)  # Action
        assert len(result.movies) > 0

    def test_list_genres(self):
        result = list_genres()
        assert "Action" in [g.name for g in result.genres]
