from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, timezone

# --- Query Schema for the main search endpoint ---

class Query(BaseModel):
    torname: str
    subtitle: Optional[str] = None
    extitle: Optional[str] = None
    imdbid: Optional[str] = None
    tmdbcat: Optional[str] = None
    tmdbid: Optional[str] = None
    infolink: Optional[str] = None

# --- TdbTorrent Schemas ---

class TdbTorrentBase(BaseModel):
    name: str
    infolink: Optional[str] = None

class TdbTorrentCreate(TdbTorrentBase):
    pass

class TdbTorrent(TdbTorrentBase):
    id: Optional[int] = None
    media_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- TdbMedia Schemas ---

class TdbMediaBase(BaseModel):
    torname_regex: Optional[str] = None
    clean_title: str
    cntitle: Optional[str] = None
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
    id_score: Optional[int] = None
    seasons: Optional[List[dict]] = None

class TdbMediaCreate(TdbMediaBase):
    pass

class TdbMediaUpdate(BaseModel):
    torname_regex: Optional[str] = None
    clean_title: Optional[str] = None
    cntitle: Optional[str] = None
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
    id_score: Optional[int] = None


class TdbMedia(TdbMediaBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    torrents: List[TdbTorrent] = []

    @field_validator('created_at', mode='before')
    @classmethod
    def make_created_at_aware(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            # Assume the naive datetime from DB is UTC
            return v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        from_attributes = True

class TdbMediaPage(BaseModel):
    items: List[TdbMedia]
    total: int
