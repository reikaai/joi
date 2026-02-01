import os

import tmdbsimple as tmdb
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel

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
def lookup_by_imdb(imdb_id: str) -> FindResult:
    """Get movie details by IMDB ID (e.g., tt0111161)"""
    find = tmdb.Find(imdb_id)
    result = find.info(external_source="imdb_id")
    return FindResult(
        movie_results=[Movie.model_validate(m) for m in result.get("movie_results", [])],
        tv_results=[TvShow.model_validate(t) for t in result.get("tv_results", [])],
    )


@mcp.tool
def find_by_name(name: str, year: int | None = None) -> MovieList:
    """Search movies by name, optionally filter by year"""
    search = tmdb.Search()
    return MovieList(movies=[Movie.model_validate(m) for m in search.movie(query=name, year=year)["results"]])


@mcp.tool
def get_recommendations(movie_id: int) -> MovieList:
    """Get recommendations for a movie"""
    movie = tmdb.Movies(movie_id)
    return MovieList(movies=[Movie.model_validate(m) for m in movie.recommendations()["results"]])


@mcp.tool
def get_similar(movie_id: int) -> MovieList:
    """Get similar movies"""
    movie = tmdb.Movies(movie_id)
    return MovieList(movies=[Movie.model_validate(m) for m in movie.similar_movies()["results"]])


@mcp.tool
def list_by_genre(genre_id: int, page: int = 1) -> MovieList:
    """List movies by genre ID"""
    discover = tmdb.Discover()
    return MovieList(movies=[Movie.model_validate(m) for m in discover.movie(with_genres=genre_id, page=page)["results"]])


@mcp.tool
def list_genres() -> GenreList:
    """List all movie genres"""
    genres = tmdb.Genres()
    return GenreList(genres=[Genre.model_validate(g) for g in genres.movie_list()["genres"]])
