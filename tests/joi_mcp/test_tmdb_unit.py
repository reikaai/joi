import pytest

from joi_mcp.tmdb import Genre, GenreList, MediaItem, MediaList, Movie, MovieList, TvShow, _movie_to_media, _tv_to_media


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

    def test_movie_list_with_pagination(self):
        data = {
            "movies": [{"id": 1, "title": "Test"}],
            "total": 100,
            "offset": 0,
            "has_more": True,
        }
        ml = MovieList.model_validate(data)
        assert len(ml.movies) == 1
        assert ml.total == 100
        assert ml.offset == 0
        assert ml.has_more is True

    def test_genre_list_with_pagination(self):
        data = {
            "genres": [{"id": 28, "name": "Action"}],
            "total": 19,
            "offset": 0,
            "has_more": False,
        }
        gl = GenreList.model_validate(data)
        assert len(gl.genres) == 1
        assert gl.total == 19
        assert gl.has_more is False


@pytest.mark.unit
class TestMediaItem:
    def test_media_item_defaults(self):
        item = MediaItem(id=1, title="Test")
        assert item.media_type == ""
        assert item.alt_titles is None
        assert item.genre_ids == []

    def test_media_item_with_alt_titles(self):
        item = MediaItem(id=1, title="Interstellar", alt_titles={"RU": "Интерстеллар", "DE": "Interstellar"})
        assert item.alt_titles is not None
        assert item.alt_titles["RU"] == "Интерстеллар"

    def test_media_list_model(self):
        data = {
            "results": [{"id": 1, "title": "Test", "media_type": "movie"}],
            "total": 1,
            "offset": 0,
            "has_more": False,
        }
        ml = MediaList.model_validate(data)
        assert len(ml.results) == 1
        assert ml.total == 1


@pytest.mark.unit
class TestMediaConversion:
    def test_movie_to_media(self):
        movie = Movie(id=157336, title="Interstellar", original_title="Interstellar", release_date="2014-11-05")
        item = _movie_to_media(movie)
        assert item.media_type == "movie"
        assert item.title == "Interstellar"
        assert item.release_date == "2014-11-05"
        assert item.alt_titles is None

    def test_movie_to_media_with_alt_titles(self):
        movie = Movie(id=157336, title="Interstellar")
        alt = {"RU": "Интерстеллар", "FR": "Interstellaire"}
        item = _movie_to_media(movie, alt)
        assert item.alt_titles == alt

    def test_tv_to_media(self):
        tv = TvShow(id=1396, name="Breaking Bad", original_name="Breaking Bad", first_air_date="2008-01-20")
        item = _tv_to_media(tv)
        assert item.media_type == "tv"
        assert item.title == "Breaking Bad"
        assert item.release_date == "2008-01-20"

    def test_tv_to_media_with_alt_titles(self):
        tv = TvShow(id=1396, name="Breaking Bad")
        alt = {"RU": "Во все тяжкие"}
        item = _tv_to_media(tv, alt)
        assert item.alt_titles == alt
