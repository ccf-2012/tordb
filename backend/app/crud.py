from sqlalchemy.orm import Session
import re
from . import models, schemas
from torcp2.torinfo import TorrentInfo
from torcp2.tmdbsearcher import TMDbSearcher
from loguru import logger
from app.utils import format_genres

# --- Read Operations ---

def get_media(db: Session, media_id: int):
    return db.query(models.Media).filter(models.Media.id == media_id).first()

from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas

def get_all_media(db: Session, skip: int = 0, limit: int = 100):
    # 1. Get the total count of distinct groups (tmdb_id)
    total_groups = db.query(func.count(models.Media.tmdb_id.distinct())).scalar()

    # 2. Get the paginated list of distinct tmdb_id's
    paginated_tmdb_ids_query = db.query(models.Media.tmdb_id).distinct().offset(skip).limit(limit)
    paginated_tmdb_ids = [id[0] for id in paginated_tmdb_ids_query.all()]

    if not paginated_tmdb_ids:
        return {"items": [], "total": total_groups}

    # 3. Get all media items that belong to the paginated tmdb_id's
    media_items = db.query(models.Media).filter(models.Media.tmdb_id.in_(paginated_tmdb_ids)).all()
    
    return {"items": media_items, "total": total_groups}

def find_torrent_by_name(db: Session, name: str) -> models.Torrent | None:
    return db.query(models.Torrent).filter(models.Torrent.name == name).first()

def find_media_by_torname_regex(db: Session, title: str) -> models.Media | None:
    all_media = db.query(models.Media).filter(models.Media.torname_regex != None).all()
    for media in all_media:
        try:
            if re.search(media.torname_regex, title, re.IGNORECASE):
                logger.info(f"Found media by regex: {media.torname_regex} for title: {title}")
                return media
        except re.error:
            continue
    return None

def find_media_by_tmdb_id(db: Session, tmdb_cat: str, tmdb_id: int) -> models.Media | None:
    return db.query(models.Media).filter(models.Media.tmdb_cat == tmdb_cat, models.Media.tmdb_id == tmdb_id).first()

def find_media_by_imdb_id(db: Session, imdb_id: str) -> models.Media | None:
    return db.query(models.Media).filter(models.Media.imdb_id == imdb_id).first()


# --- Create Operations ---

def create_media(db: Session, torinfo: TorrentInfo) -> models.Media:
    tmdb_genres = format_genres(torinfo)

    media_create = schemas.MediaCreate(
        torname_regex=torinfo.media_title,
        tmdb_id=torinfo.tmdb_id,
        tmdb_title=torinfo.tmdb_title,
        tmdb_cat=torinfo.tmdb_cat,
        tmdb_poster=torinfo.poster_path,
        tmdb_year=torinfo.year,
        imdb_id=torinfo.imdb_id,
        tmdb_overview=torinfo.overview,
        original_language=torinfo.original_language,
        release_air_date=torinfo.release_air_date,
        origin_country=torinfo.origin_country,
        original_title=torinfo.original_title,
        production_countries=torinfo.production_countries,
        tmdb_genres=tmdb_genres
    )
    db_media = models.Media(**media_create.model_dump())
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media

def create_torrent(db: Session, torinfo: TorrentInfo, media_id: int) -> models.Torrent:
    torrent_create = schemas.TorrentCreate(name=torinfo.torname, infolink=torinfo.infolink)
    db_torrent = models.Torrent(**torrent_create.model_dump(), media_id=media_id)
    db.add(db_torrent)
    db.commit()
    db.refresh(db_torrent)
    return db_torrent

# --- Update Operations ---

def update_media(db: Session, media_id: int, media_update: schemas.MediaUpdate) -> models.Media | None:
    db_media = get_media(db, media_id)
    if db_media:
        for key, value in media_update.model_dump(exclude_unset=True).items():
            setattr(db_media, key, value)
        db.commit()
        db.refresh(db_media)
    return db_media

# --- Delete Operations ---

def delete_media(db: Session, media_id: int) -> models.Media | None:
    db_media = get_media(db, media_id)
    if db_media:
        db.delete(db_media)
        db.commit()
    return db_media

def delete_torrent(db: Session, torrent_id: int) -> models.Torrent | None:
    db_torrent = db.query(models.Torrent).filter(models.Torrent.id == torrent_id).first()
    if db_torrent:
        db.delete(db_torrent)
        db.commit()
    return db_torrent

# --- Main Search Logic ---

def search_and_create_media(db: Session, torinfo: TorrentInfo, searcher: TMDbSearcher) -> models.Media | None:
    # 1. Exact torrent name match
    if torrent := find_torrent_by_name(db, torinfo.torname):
        logger.info(f"LOCAL: Found existing torrent by name: {torinfo.torname}")
        return torrent.media

    # 2. TMDb ID provided
    if torinfo.tmdb_id and torinfo.tmdb_cat:
        logger.info(f"INFO: TMDb ID provided: {torinfo.tmdb_cat}-{torinfo.tmdb_id}")
        if media := find_media_by_tmdb_id(db, torinfo.tmdb_cat, torinfo.tmdb_id):
            logger.info(f"LOCAL: Found media by TMDb ID: {media.tmdb_title}")
            create_torrent(db, torinfo, media.id)
            return media
        else:
            # If not in local DB, fetch from TMDb and create
            if searcher.search_tmdb_by_tmdbid(torinfo):
                logger.info(f"TMDb: Found media by TMDb ID: {torinfo.tmdb_title}")
                new_media = create_media(db, torinfo)
                create_torrent(db, torinfo, new_media.id)
                return new_media

    # 3. IMDb ID provided (for movies)
    if torinfo.imdb_id and torinfo.tmdb_cat == 'movie':
        logger.info(f"INFO: IMDb ID provided: {torinfo.imdb_id}")
        if media := find_media_by_imdb_id(db, torinfo.imdb_id):
            logger.info(f"LOCAL: Found media by IMDb ID: {media.tmdb_title}")
            create_torrent(db, torinfo, media.id)
            return media
        else:
            # If not in local DB, fetch from TMDb and create
            if searcher.searchTMDbByIMDbId(torinfo):
                logger.info(f"TMDb: Found media by IMDb ID: {torinfo.tmdb_title}")
                new_media = create_media(db, torinfo)
                create_torrent(db, torinfo, new_media.id)
                return new_media

    # 4. Regex match on torrent name
    if media := find_media_by_torname_regex(db, torinfo.media_title):
        logger.info(f"LOCAL: Found media by regex: {torinfo.media_title}")
        create_torrent(db, torinfo, media.id)
        return media

    # 5. Blind search on TMDb
    logger.info(f"INFO: No local match found. Performing blind search on TMDb for: {torinfo.media_title}")
    if searcher.searchTMDb(torinfo):
        # After blind search, torinfo is populated with TMDb data.
        # Check again if this TMDb ID already exists locally.
        if media := find_media_by_tmdb_id(db, torinfo.tmdb_cat, torinfo.tmdb_id):
            logger.info(f"LOCAL: Found media by TMDb ID after blind search: {media.tmdb_title}")
            create_torrent(db, torinfo, media.id)
            return media

        # If confidence is too low, reject
        if torinfo.confidence < 30:
            logger.warning(f"BLIND confidence too low: {torinfo.confidence} for {torinfo.torname}")
            return None

        # Create new media and torrent
        logger.info(f"TMDb: Found media by blind search: {torinfo.tmdb_title}")
        new_media = create_media(db, torinfo)
        create_torrent(db, torinfo, new_media.id)
        return new_media

    logger.warning(f"FAIL: Could not find any match for: {torinfo.torname}")
    return None