import os

import tmdbsimple as tmdb
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel

from joi_mcp.pagination import DEFAULT_LIMIT, paginate
from joi_mcp.query import apply_query

load_dotenv()

mcp = FastMCP("TMDB")
if not tmdb.API_KEY:
    tmdb.API_KEY = os.getenv("TMDB_API_KEY")


class Movie(BaseModel):
    id: int
    title: str
    original_title: str = ""
    overview: str = ""
    release_date: str = ""
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0
    adult: bool = False
    video: bool = False
    genre_ids: list[int] = []
    original_language: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None


class TvShow(BaseModel):
    id: int
    name: str
    original_name: str = ""
    overview: str = ""
    first_air_date: str = ""
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0
    adult: bool = False
    genre_ids: list[int] = []
    original_language: str = ""
    origin_country: list[str] = []
    poster_path: str | None = None
    backdrop_path: str | None = None


class Genre(BaseModel):
    id: int
    name: str


class MovieList(BaseModel):
    movies: list[Movie]
    total: int
    offset: int
    has_more: bool


class GenreList(BaseModel):
    genres: list[Genre]
    total: int
    offset: int
    has_more: bool


class FindResult(BaseModel):
    movie_results: list[Movie]
    tv_results: list[TvShow]
    movie_total: int
    tv_total: int


@mcp.tool
def lookup_by_imdb(
    imdb_id: str,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> FindResult:
    """Get movie details by IMDB ID (e.g., tt0111161)

    Args:
        imdb_id: IMDB ID (e.g. "tt0111161")
        filter_expr: JMESPath filter for results
        sort_by: Field to sort by, prefix - for desc
        limit: Max results per list (default 50)
    """
    find = tmdb.Find(imdb_id)
    result = find.info(external_source="imdb_id")
    movies = [Movie.model_validate(m) for m in result.get("movie_results", [])]
    tv_shows = [TvShow.model_validate(t) for t in result.get("tv_results", [])]
    filtered_movies = apply_query(movies, filter_expr, sort_by, limit)
    filtered_tv = apply_query(tv_shows, filter_expr, sort_by, limit)
    return FindResult(
        movie_results=filtered_movies,
        tv_results=filtered_tv,
        movie_total=len(movies),
        tv_total=len(tv_shows),
    )


@mcp.tool
def search_movies(
    name: str,
    year: int | None = None,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> MovieList:
    """Search movies by name with pagination

    Args:
        name: Movie name to search
        year: Filter by release year
        filter_expr: JMESPath filter (e.g. "vote_average > `7`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-popularity")
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    search = tmdb.Search()
    movies = [Movie.model_validate(m) for m in search.movie(query=name, year=year)["results"]]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return MovieList(movies=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def get_recommendations(
    movie_id: int,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> MovieList:
    """Get recommendations for a movie with pagination

    Args:
        movie_id: TMDB movie ID
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    movie = tmdb.Movies(movie_id)
    movies = [Movie.model_validate(m) for m in movie.recommendations()["results"]]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return MovieList(movies=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def get_similar(
    movie_id: int,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> MovieList:
    """Get similar movies with pagination

    Args:
        movie_id: TMDB movie ID
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    movie = tmdb.Movies(movie_id)
    movies = [Movie.model_validate(m) for m in movie.similar_movies()["results"]]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return MovieList(movies=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def list_movies_by_genre(
    genre_id: int,
    page: int = 1,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> MovieList:
    """List movies by genre ID with pagination

    Args:
        genre_id: TMDB genre ID
        page: TMDB page number
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    discover = tmdb.Discover()
    movies = [Movie.model_validate(m) for m in discover.movie(with_genres=genre_id, page=page)["results"]]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return MovieList(movies=paginated, total=total, offset=offset, has_more=has_more)


@mcp.tool
def list_genres(
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> GenreList:
    """List all movie genres with pagination

    Args:
        filter_expr: JMESPath filter (e.g. "contains(name, 'Action')")
        sort_by: Field to sort by, prefix - for desc (e.g. "name")
        limit: Max results (default 50)
        offset: Starting position (default 0)
    """
    genres_api = tmdb.Genres()
    genres = [Genre.model_validate(g) for g in genres_api.movie_list()["genres"]]
    filtered = apply_query(genres, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    return GenreList(genres=paginated, total=total, offset=offset, has_more=has_more)
