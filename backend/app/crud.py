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
from sqlalchemy import func, or_
from . import models, schemas

def get_all_media(db: Session, skip: int = 0, limit: int = 100):
    # Query for paginated media items, sorted by creation date
    items = db.query(models.Media).order_by(models.Media.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get the total count of all media items for pagination
    total = db.query(func.count(models.Media.id)).scalar()
    
    return {"items": items, "total": total}

def search_media(db: Session, q: str):
    search_query = f"%{q}%"
    
    # Query for media items matching the search query in either tmdb_title or clean_title
    media_items = db.query(models.Media).filter(
        or_(
            models.Media.tmdb_title.ilike(search_query),
            models.Media.clean_title.ilike(search_query)
        )
    ).all()
    
    # Since the search result is not paginated in the same way, we can count the total results directly.
    # For consistency, we can still group by tmdb_id if needed, but for now, we'll return the flat list.
    # The frontend will need to handle this structure.
    
    total_results = len(media_items)
    
    return {"items": media_items, "total": total_results}

def find_torrent_by_name(db: Session, name: str) -> models.Torrent | None:
    return db.query(models.Torrent).filter(models.Torrent.name == name).first()

def find_media_by_torinfo(db: Session, torinfo: TorrentInfo) -> models.Media | None:
    # TODO: 这里要求传入的torinfo.clean_title 等于数据库中的值，但是有时是非常像，只有一个空格符号没对上就不会匹配
    candidates = db.query(models.Media).filter(models.Media.clean_title == torinfo.clean_title).all()
    if not candidates:
        return None

    # Now, try to find the best match among the candidates
    for media in candidates:
        # Score based on matching attributes
        score = 0
        # 类型不对，先扣分，试试看还能不能加回来
        if torinfo.tmdb_cat != media.tmdb_cat:
            score -= 6

        # 匹配字串长度加分
        if len(torinfo.clean_title) >= 4:
            score += 2

        # 年份相差1年内，对 movie 和 S01的剧有效
        if torinfo.tmdb_cat == 'movie' or torinfo.season == 'S01':
            if torinfo.year and media.tmdb_year and abs(media.tmdb_year - int(torinfo.year)) <= 1:
                score += 3

        # 有 cntitle (种子名中解析出) 或 extitle (单独提供，由subtitle解析出) 且匹配
        if torinfo.cntitle and torinfo.cntitle in (media.cntitle, media.tmdb_title):
            score += 3
        if torinfo.extitle and torinfo.extitle in (media.cntitle, media.tmdb_title):
            score += 4
        
        # TODO: 字符长度4+, year, cntitle, extitle 至少匹配一个
        if score >= 2:
            logger.info(f"Found media by torinfo: {media.tmdb_title} with score {score}")
            return media

    # If no high-score match is found, return the first candidate as a fallback
    # This preserves the old behavior if no other signals are present.
    logger.info(f"Fallback: Found media by clean_title: {candidates[0].tmdb_title}")
    return candidates[0]

def find_media_by_torname_regex(db: Session, title: str, clean_title: str) -> models.Media | None:
    all_media_with_regex = db.query(models.Media).filter(
        models.Media.torname_regex != None,
        # models.Media.clean_title.like(f"%{clean_title}%") # 加上后只能查到 clean_title 比库里的短的
    ).all()
    for media in all_media_with_regex:
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

def create_media(db: Session, media: schemas.MediaCreate) -> models.Media:
    db_media = models.Media(**media.model_dump())
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media


def _create_media_schema_from_torinfo(torinfo: TorrentInfo) -> schemas.MediaCreate:
    """Helper function to create a MediaCreate schema from a TorrentInfo object."""
    tmdb_genres = format_genres(torinfo)
    return schemas.MediaCreate(
        clean_title=torinfo.clean_title,
        cntitle=torinfo.cntitle,
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
        tmdb_genres=tmdb_genres,
        id_score=torinfo.id_score,
        seasons=torinfo.seasons,
    )

def create_media_from_torinfo(db: Session, torinfo: TorrentInfo) -> models.Media:
    """Creates a media item from a TorrentInfo object and saves it to the database."""
    media_create = _create_media_schema_from_torinfo(torinfo)
    return create_media(db, media_create)

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

def search_and_create_media(db: Session, torinfo: TorrentInfo, searcher: TMDbSearcher) -> models.Media | schemas.Media | None:
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
                new_media = create_media_from_torinfo(db, torinfo)
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
            if searcher.search_by_imdb_id(torinfo):
                logger.info(f"TMDb: Found media by IMDb ID: {torinfo.tmdb_title}")
                new_media = create_media_from_torinfo(db, torinfo)
                create_torrent(db, torinfo, new_media.id)
                # TODO: 保存 clean_title 和 对应的tmdb_id/tmdb_cat, 以便后续查询可用
                return new_media

    # 4. 通过 clean_title(media_title) 进行匹配
    if media := find_media_by_torinfo(db, torinfo):
        # 根据 torname_regex 进行确认：stip_title 匹配上了，但是如果用户手工指定了 torname_regex 则在此进行检查
        if media.torname_regex:
            if not re.search(media.torname_regex, torinfo.torname, re.IGNORECASE):
                logger.info(f"LOCAL: rejected by torname_regex: {torinfo.torname}, clean_title: {torinfo.clean_title}")
                return None
        logger.info(f"LOCAL: Found media by clean_title: {torinfo.clean_title}")
        create_torrent(db, torinfo, media.id)
        return media
          
    # 5. Regex match on torrent name
    # 所有 torname_regex 是用户手工设置，对全 torname 进行匹配
    if media := find_media_by_torname_regex(db, torinfo.torname, torinfo.clean_title):
        logger.info(f"LOCAL: Found media by regex: {torinfo.torname}")
        create_torrent(db, torinfo, media.id)
        return media

    # 6. Blind search on TMDb
    logger.info(f"INFO: No local match found. Performing blind search on TMDb for: {torinfo.clean_title}, {torinfo.cntitle}, {torinfo.extitle}")
    # strip_tile本地没有，以从torname 中解析出的 clean_title, cntitle 和 subtitle 解析出的 extitle，进行 search_tmdb
    if searcher.search_tmdb(torinfo):
        # After blind search, torinfo is populated with TMDb data.
        # Check again if this TMDb ID already exists locally.
        # TODO: strip title 有问题？
        if media := find_media_by_tmdb_id(db, torinfo.tmdb_cat, torinfo.tmdb_id):
            logger.info(f"LOCAL: Found media by TMDb ID after blind search: {media.tmdb_title}")
            create_torrent(db, torinfo, media.id)
            return media

        # If score is too low, do not save to DB, but return the result for caller.
        logger.debug(f"score: {torinfo.id_score}")
        if torinfo.id_score < 19:
            logger.warning(f"BLIND id_score too low: {torinfo.id_score} for {torinfo.torname}")
            # Manually create the Pydantic schema object to avoid SQLAlchemy conversion issues
            media_data = _create_media_schema_from_torinfo(torinfo)
            torrent_data = schemas.TorrentCreate(name=torinfo.torname, infolink=torinfo.infolink)

            # Create a full Media schema object from the data
            response_media = schemas.Media(**media_data.model_dump())
            
            # Create the Torrent schema object and add it to the list
            response_media.torrents.append(schemas.Torrent(**torrent_data.model_dump()))

            # The function's return type is now updated to reflect this possibility
            return response_media

        # Create new media and torrent
        logger.info(f"TMDb: Found media by blind search: {torinfo.tmdb_title}")
        # TODO: 保存 clean_title 以便后续查询
        new_media = create_media_from_torinfo(db, torinfo)
        create_torrent(db, torinfo, new_media.id)
        return new_media

    logger.warning(f"FAIL: Could not find any match for: {torinfo.torname}")
    return None