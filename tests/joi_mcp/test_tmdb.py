import pytest

from joi_mcp.tmdb import (
    discover_movies,
    list_genres,
    search_media,
)


@pytest.mark.contract
@pytest.mark.vcr
class TestTMDBContract:
    def test_search_media_movie(self):
        result = search_media(query="The Matrix", year=1999, media_type="movie")
        assert len(result.results) > 0
        assert "Matrix" in result.results[0].title

    def test_search_media_tv(self):
        result = search_media(query="Breaking Bad", media_type="tv")
        assert len(result.results) > 0
        assert "Breaking Bad" in result.results[0].title

    def test_search_media_by_imdb_movie(self):
        result = search_media(imdb_id="tt0133093")  # The Matrix
        assert len(result.results) >= 1
        matrix = [r for r in result.results if r.media_type == "movie"]
        assert len(matrix) == 1
        assert matrix[0].title == "The Matrix"
        assert matrix[0].alt_titles is not None

    def test_search_media_by_imdb_tv(self):
        result = search_media(imdb_id="tt0903747")  # Breaking Bad
        assert len(result.results) >= 1
        bb = [r for r in result.results if r.media_type == "tv"]
        assert len(bb) == 1
        assert bb[0].title == "Breaking Bad"
        assert bb[0].alt_titles is not None

    def test_get_recommendations(self):
        result = discover_movies(source="recommendations", movie_id=603)
        assert len(result.movies) > 0

    def test_get_similar(self):
        result = discover_movies(source="similar", movie_id=603)
        assert len(result.movies) > 0

    def test_list_movies_by_genre(self):
        result = discover_movies(source="genre", genre_id=28)
        assert len(result.movies) > 0

    def test_list_genres(self):
        result = list_genres()
        assert "Action" in [g.name for g in result.genres]
