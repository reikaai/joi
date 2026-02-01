import pytest

from joi_mcp.tmdb import Genre, Movie, TvShow


@pytest.mark.unit
class TestModels:
    def test_movie_parses_full_response(self):
        data = {
            "id": 603,
            "title": "The Matrix",
            "original_title": "The Matrix",
            "overview": "A computer hacker...",
            "release_date": "1999-03-30",
            "popularity": 83.5,
            "vote_average": 8.2,
            "vote_count": 24000,
            "adult": False,
            "video": False,
            "genre_ids": [28, 878],
            "original_language": "en",
            "poster_path": "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
            "backdrop_path": "/fNG7i7RqMErkcqhohV2a6cV1Ehy.jpg",
        }
        movie = Movie.model_validate(data)
        assert movie.id == 603
        assert movie.title == "The Matrix"
        assert movie.genre_ids == [28, 878]

    def test_movie_handles_missing_optional_fields(self):
        data = {"id": 1, "title": "Test"}
        movie = Movie.model_validate(data)
        assert movie.poster_path is None
        assert movie.genre_ids == []

    def test_tvshow_parses_full_response(self):
        data = {
            "id": 1396,
            "name": "Breaking Bad",
            "original_name": "Breaking Bad",
            "overview": "A high school chemistry teacher...",
            "first_air_date": "2008-01-20",
            "popularity": 400.5,
            "vote_average": 9.5,
            "vote_count": 12000,
            "adult": False,
            "genre_ids": [18, 80],
            "original_language": "en",
            "origin_country": ["US"],
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
        }
        tv = TvShow.model_validate(data)
        assert tv.name == "Breaking Bad"
        assert tv.origin_country == ["US"]

    def test_genre_model(self):
        genre = Genre.model_validate({"id": 28, "name": "Action"})
        assert genre.id == 28
        assert genre.name == "Action"
