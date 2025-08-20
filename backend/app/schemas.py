from pydantic import BaseModel
from typing import List, Optional

# --- Query Schema for the main search endpoint ---

class Query(BaseModel):
    torname: str
    extitle: Optional[str] = None
    imdbid: Optional[str] = None
    tmdbstr: Optional[str] = None
    infolink: Optional[str] = None

# --- Torrent Schemas ---

class TorrentBase(BaseModel):
    name: str
    infolink: Optional[str] = None

class TorrentCreate(TorrentBase):
    pass

class Torrent(TorrentBase):
    id: int
    media_id: int

    class Config:
        from_attributes = True

# --- Media Schemas ---

class MediaBase(BaseModel):
    torname_regex: str
    tmdb_id: Optional[int] = None
    tmdb_title: Optional[str] = None
    tmdb_cat: Optional[str] = None
    tmdb_poster: Optional[str] = None
    tmdb_year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_genres: Optional[str] = None
    tmdb_overview: Optional[str] = None
    original_language: Optional[str] = None
    release_air_date: Optional[str] = None
    origin_country: Optional[str] = None
    original_title: Optional[str] = None
    production_countries: Optional[str] = None
    custom_title: Optional[str] = None
    custom_path: Optional[str] = None

class MediaCreate(MediaBase):
    pass

class MediaUpdate(MediaBase):
    torname_regex: Optional[str] = None
    tmdb_id: Optional[int] = None
    tmdb_title: Optional[str] = None
    tmdb_cat: Optional[str] = None
    tmdb_poster: Optional[str] = None
    tmdb_year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_genres: Optional[str] = None
    tmdb_overview: Optional[str] = None
    original_language: Optional[str] = None
    release_air_date: Optional[str] = None
    origin_country: Optional[str] = None
    original_title: Optional[str] = None
    production_countries: Optional[str] = None
    custom_title: Optional[str] = None
    custom_path: Optional[str] = None

class Media(MediaBase):
    id: int
    torrents: List[Torrent] = []

    class Config:
        from_attributes = True

class MediaPage(BaseModel):
    items: List[Media]
    total: int