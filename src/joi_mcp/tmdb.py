import os

import tmdbsimple as tmdb
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel

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


class GenreList(BaseModel):
    genres: list[Genre]


class FindResult(BaseModel):
    movie_results: list[Movie]
    tv_results: list[TvShow]


@mcp.tool
def lookup_by_imdb(
    imdb_id: str,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> FindResult:
    """Get movie details by IMDB ID (e.g., tt0111161)

    Args:
        imdb_id: IMDB ID (e.g. "tt0111161")
        filter_expr: JMESPath filter for results
        sort_by: Field to sort by, prefix - for desc
        limit: Max results per list
    """
    find = tmdb.Find(imdb_id)
    result = find.info(external_source="imdb_id")
    movies = [Movie.model_validate(m) for m in result.get("movie_results", [])]
    tv_shows = [TvShow.model_validate(t) for t in result.get("tv_results", [])]
    return FindResult(
        movie_results=apply_query(movies, filter_expr, sort_by, limit),
        tv_results=apply_query(tv_shows, filter_expr, sort_by, limit),
    )


@mcp.tool
def search_movies(
    name: str,
    year: int | None = None,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> MovieList:
    """Search movies by name, optionally filter by year

    Args:
        name: Movie name to search
        year: Filter by release year
        filter_expr: JMESPath filter (e.g. "vote_average > `7`")
        sort_by: Field to sort by, prefix - for desc (e.g. "-popularity")
        limit: Max results
    """
    search = tmdb.Search()
    movies = [Movie.model_validate(m) for m in search.movie(query=name, year=year)["results"]]
    return MovieList(movies=apply_query(movies, filter_expr, sort_by, limit))


@mcp.tool
def get_recommendations(
    movie_id: int,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> MovieList:
    """Get recommendations for a movie

    Args:
        movie_id: TMDB movie ID
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results
    """
    movie = tmdb.Movies(movie_id)
    movies = [Movie.model_validate(m) for m in movie.recommendations()["results"]]
    return MovieList(movies=apply_query(movies, filter_expr, sort_by, limit))


@mcp.tool
def get_similar(
    movie_id: int,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> MovieList:
    """Get similar movies

    Args:
        movie_id: TMDB movie ID
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results
    """
    movie = tmdb.Movies(movie_id)
    movies = [Movie.model_validate(m) for m in movie.similar_movies()["results"]]
    return MovieList(movies=apply_query(movies, filter_expr, sort_by, limit))


@mcp.tool
def list_movies_by_genre(
    genre_id: int,
    page: int = 1,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> MovieList:
    """List movies by genre ID

    Args:
        genre_id: TMDB genre ID
        page: Page number
        filter_expr: JMESPath filter
        sort_by: Field to sort by, prefix - for desc
        limit: Max results
    """
    discover = tmdb.Discover()
    movies = [Movie.model_validate(m) for m in discover.movie(with_genres=genre_id, page=page)["results"]]
    return MovieList(movies=apply_query(movies, filter_expr, sort_by, limit))


@mcp.tool
def list_genres(
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> GenreList:
    """List all movie genres

    Args:
        filter_expr: JMESPath filter (e.g. "contains(name, 'Action')")
        sort_by: Field to sort by, prefix - for desc (e.g. "name")
        limit: Max results
    """
    genres_api = tmdb.Genres()
    genres = [Genre.model_validate(g) for g in genres_api.movie_list()["genres"]]
    return GenreList(genres=apply_query(genres, filter_expr, sort_by, limit))
