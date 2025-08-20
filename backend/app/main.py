import os
import sys
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Adjust sys.path to allow imports from the parent `backend` directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'torcp2')))

from torcp2.tmdbsearcher import TMDbSearcher
from torcp2.torinfo import TorrentParser, TorrentInfo
from app import crud, models, schemas
from app.models import SessionLocal, create_db_and_tables
from app.config import settings
from app.utils import format_genres

app = FastAPI()

# Initialize TMDbSearcher at startup using the key from config
# pydantic will raise an error on startup if the key is missing.
searcher = TMDbSearcher(tmdb_api_key=settings.tmdb_api_key)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_tmdb_str(tmdb_str: str):
    if not tmdb_str or '-' not in tmdb_str:
        return None, None
    parts = tmdb_str.split('-')
    return parts[0], parts[1] if len(parts) > 1 else None

@app.post("/api/query", response_model=schemas.Media)
def search_media_by_torname_post(query: schemas.Query, db: Session = Depends(get_db)):
    """
    This endpoint mirrors the logic of the original Flask query, accepting a JSON body.
    """
    torinfo = TorrentParser.parse(query.torname)
    if not torinfo.media_title:
        raise HTTPException(status_code=400, detail="Could not parse a valid media title from torname")

    # Augment torinfo with optional data from the query payload
    if query.extitle:
        torinfo.subtitle = query.extitle
    if query.imdbid:
        torinfo.imdb_id = query.imdbid
    if query.tmdbstr:
        torinfo.tmdb_cat, torinfo.tmdb_id = parse_tmdb_str(query.tmdbstr)
    if query.infolink:
        torinfo.infolink = query.infolink

    # Call the main search logic in crud
    media_result = crud.search_and_create_media(db, torinfo, searcher)

    if media_result:
        return media_result
    
    raise HTTPException(status_code=404, detail=f"Could not find or create a media match for \"{query.torname}\"")

# --- Standard CRUD for Media ---
@app.post("/api/media/", response_model=schemas.Media)
def create_media(media: schemas.MediaCreate, db: Session = Depends(get_db)):
    return crud.create_media(db=db, media=media)

@app.post("/api/media/from-tmdb/", response_model=schemas.Media)
def create_media_from_tmdb(
    torname_regex: str,
    tmdb_cat: str,
    tmdb_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Fetch details from TMDb using TorrentInfo
        n1 = TorrentInfo()
        n1.tmdb_cat = tmdb_cat
        n1.tmdb_id = str(tmdb_id)
        r = searcher.search_tmdb_by_tmdbid(n1)

        if not r:
            raise HTTPException(status_code=404, detail=f"Could not find TMDb details for ID {tmdb_id} and category {tmdb_cat}")

        # Extract details from the populated TorrentInfo object
        tmdb_title = n1.tmdb_title
        tmdb_poster = n1.poster_path
        tmdb_year = int(n1.release_air_date[:4]) if n1.release_air_date else None

        tmdb_genres = format_genres(n1)
        tmdb_overview = n1.overview

        media_create = schemas.MediaCreate(
            torname_regex=torname_regex,
            tmdb_id=tmdb_id,
            tmdb_title=tmdb_title,
            tmdb_cat=tmdb_cat,
            tmdb_poster=tmdb_poster,
            tmdb_year=tmdb_year,
            tmdb_genres=tmdb_genres,
            tmdb_overview=tmdb_overview
        )
        new_media = crud.create_media(db, media_create)
        return new_media
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create media from TMDb: {e}")

@app.get("/api/media/", response_model=schemas.MediaPage)
def read_all_media(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_all_media(db, skip=skip, limit=limit)

@app.get("/api/media/{media_id}", response_model=schemas.Media)
def read_media(media_id: int, db: Session = Depends(get_db)):
    db_media = crud.get_media(db, media_id=media_id)
    if db_media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return db_media

@app.put("/api/media/{media_id}", response_model=schemas.Media)
def update_media(media_id: int, media: schemas.MediaUpdate, db: Session = Depends(get_db)):
    db_media = crud.update_media(db, media_id, media)
    if db_media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return db_media

@app.delete("/api/media/{media_id}", response_model=schemas.Media)
def delete_media(media_id: int, db: Session = Depends(get_db)):
    db_media = crud.delete_media(db, media_id)
    if db_media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return db_media

@app.get("/api/tmdb/details", response_model=dict)
def get_tmdb_details(tmdb_id: int, tmdb_cat: str):
    n1 = TorrentInfo()
    n1.tmdb_cat = tmdb_cat
    n1.tmdb_id = str(tmdb_id)
    r = searcher.search_tmdb_by_tmdbid(n1)
    if not r:
        raise HTTPException(status_code=404, detail=f"TMDb details not found for ID {tmdb_id} and category {tmdb_cat}")

    tmdb_details_dict = {
        "title": n1.tmdb_title,
        "name": n1.tmdb_title,
        "poster_path": n1.poster_path,
        "release_date": n1.release_air_date,
        "overview": n1.overview,
        "genres": [],
        "id": n1.tmdb_id,
        "media_type": n1.tmdb_cat,
        "vote_average": n1.vote_average,
        "popularity": n1.popularity,
        "original_language": n1.original_language,
        "original_title": n1.original_title,
        "origin_country": n1.origin_country,
        "production_countries": n1.production_countries,
        "year": n1.year
    }

    if n1.tmdbDetails and hasattr(n1.tmdbDetails, 'genres'):
        tmdb_details_dict["genres"] = [{"id": g.id, "name": g.name} for g in n1.tmdbDetails.genres]
    elif n1.genre_ids:
        tmdb_details_dict["genres"] = [{"name": g} for g in n1.genre_ids]

    return tmdb_details_dict

# --- Standard CRUD for Torrents ---
@app.post("/api/torrents/", response_model=schemas.Torrent)
def create_torrent_for_media(media_id: int, torrent: schemas.TorrentCreate, db: Session = Depends(get_db)):
    db_media = crud.get_media(db, media_id=media_id)
    if db_media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return crud.create_torrent(db=db, torrent=torrent, media_id=media_id)

@app.delete("/api/torrents/{torrent_id}", response_model=schemas.Torrent)
def delete_torrent(torrent_id: int, db: Session = Depends(get_db)):
    db_torrent = crud.delete_torrent(db, torrent_id)
    if db_torrent is None:
        raise HTTPException(status_code=404, detail="Torrent not found")
    return db_torrent
