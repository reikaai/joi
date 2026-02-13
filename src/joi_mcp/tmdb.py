import os
from typing import Annotated, Any, Literal

import tmdbsimple as tmdb
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from joi_mcp.pagination import DEFAULT_LIMIT, paginate
from joi_mcp.query import apply_query, project
from joi_mcp.schema import optimize_tool_schemas

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
    movies: list[Movie] | list[dict[str, Any]]
    total: int
    offset: int
    has_more: bool


class GenreList(BaseModel):
    genres: list[Genre] | list[dict[str, Any]]
    total: int
    offset: int
    has_more: bool


class FindResult(BaseModel):
    movie_results: list[Movie] | list[dict[str, Any]]
    tv_results: list[TvShow] | list[dict[str, Any]]
    movie_total: int
    tv_total: int


@mcp.tool
def lookup_by_imdb(
    imdb_id: Annotated[str, Field(description="IMDB ID (tt0111161)")],
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields (id auto-incl.)")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
) -> FindResult:
    """Lookup by IMDB ID. Fields: title/name, overview, release_date/first_air_date, popularity, vote_average, genre_ids"""
    find = tmdb.Find(imdb_id)
    result = find.info(external_source="imdb_id")
    movies = [Movie.model_validate(m) for m in result.get("movie_results", [])]
    tv_shows = [TvShow.model_validate(t) for t in result.get("tv_results", [])]
    filtered_movies = apply_query(movies, filter_expr, limit=limit)
    filtered_tv = apply_query(tv_shows, filter_expr, limit=limit)
    return FindResult(
        movie_results=project(filtered_movies, fields),
        tv_results=project(filtered_tv, fields),
        movie_total=len(movies),
        tv_total=len(tv_shows),
    )


@mcp.tool
def search_movies(
    name: Annotated[str, Field()],
    year: Annotated[int | None, Field(description="Release year")] = None,
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields (id auto-incl.)")] = None,
    sort_by: Annotated[str | None, Field(description="Sort field, - prefix for desc")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
    offset: Annotated[int, Field()] = 0,
) -> MovieList:
    """Search movies. Fields: title, overview, release_date, popularity, vote_average, genre_ids, poster_path"""
    search = tmdb.Search()
    movies = [Movie.model_validate(m) for m in search.movie(query=name, year=year)["results"]]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    projected = project(paginated, fields)
    return MovieList(movies=projected, total=total, offset=offset, has_more=has_more)


@mcp.tool
def discover_movies(
    source: Annotated[Literal["recommendations", "similar", "genre"], Field(
        description="Source: recommendations/similar (movie_id) or genre (genre_id)"
    )],
    movie_id: Annotated[int | None, Field(description="TMDB movie ID")] = None,
    genre_id: Annotated[int | None, Field(description="TMDB genre ID")] = None,
    page: Annotated[int, Field()] = 1,
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields (id auto-incl.)")] = None,
    sort_by: Annotated[str | None, Field(description="Sort field, - prefix for desc")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
    offset: Annotated[int, Field()] = 0,
) -> MovieList:
    """Discover movies by recommendations, similarity, or genre. Fields: title, overview, release_date, vote_average, genre_ids"""
    if source in ("recommendations", "similar"):
        if movie_id is None:
            raise ValueError(f"movie_id required for source={source}")
        movie = tmdb.Movies(movie_id)
        raw = movie.recommendations()["results"] if source == "recommendations" else movie.similar_movies()["results"]
    else:
        if genre_id is None:
            raise ValueError("genre_id required for source=genre")
        raw = tmdb.Discover().movie(with_genres=genre_id, page=page)["results"]

    movies = [Movie.model_validate(m) for m in raw]
    filtered = apply_query(movies, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, offset)
    projected = project(paginated, fields)
    return MovieList(movies=projected, total=total, offset=offset, has_more=has_more)


@mcp.tool
def list_genres(
    filter_expr: Annotated[str | None, Field(description="JMESPath filter; search(@, 'text') for text search")] = None,
    fields: Annotated[list[str] | None, Field(description="Fields (id auto-incl.)")] = None,
    sort_by: Annotated[str | None, Field(description="Sort field, - prefix for desc")] = None,
    limit: Annotated[int, Field()] = DEFAULT_LIMIT,
) -> GenreList:
    """List movie genres. Fields: name"""
    genres_api = tmdb.Genres()
    genres = [Genre.model_validate(g) for g in genres_api.movie_list()["genres"]]
    filtered = apply_query(genres, filter_expr, sort_by, limit=None)
    paginated, total, has_more = paginate(filtered, limit, 0)
    projected = project(paginated, fields)
    return GenreList(genres=projected, total=total, offset=0, has_more=has_more)


optimize_tool_schemas(mcp)
