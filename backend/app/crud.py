from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_  
import re
from . import models, schemas
from torcp2.torinfo import TorrentInfo
from torcp2.tmdbsearcher import TMDbSearcher
from loguru import logger

# --- Read Operations ---

def get_media(db: Session, media_id: int):
    return db.query(models.TdbMedia).filter(models.TdbMedia.id == media_id).first()

def get_all_media(db: Session, skip: int = 0, limit: int = 100):
    # Query for paginated media items, sorted by creation date
    items = db.query(models.TdbMedia).order_by(models.TdbMedia.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get the total count of all media items for pagination
    total = db.query(func.count(models.TdbMedia.id)).scalar()
    
    return {"items": items, "total": total}

def search_media(db: Session, q: str):
    search_query = f"%{q}%"
    
    # Query for media items matching the search query in either tmdb_title or clean_title
    media_items = db.query(models.TdbMedia).filter(
        or_(
            models.TdbMedia.tmdb_title.ilike(search_query),
            models.TdbMedia.clean_title.ilike(search_query)
        )
    ).all()
    
    # Since the search result is not paginated in the same way, we can count the total results directly.
    # For consistency, we can still group by tmdb_id if needed, but for now, we'll return the flat list.
    # The frontend will need to handle this structure.
    
    total_results = len(media_items)
    
    return {"items": media_items, "total": total_results}

def find_torrent_by_name(db: Session, name: str) -> models.TdbTorrent | None:
    return db.query(models.TdbTorrent).filter(models.TdbTorrent.name == name).first()

def find_media_by_torinfo(db: Session, torinfo: TorrentInfo) -> models.TdbMedia | None:
    # # 1. Aggregate all potential titles from torinfo
    # search_titles = {torinfo.clean_title, torinfo.cntitle, torinfo.extitle}
    # # Filter out None or empty strings
    # search_titles = {title for title in search_titles if title}

    # if not search_titles:
    #     return None

    # 2. Query the database using the aggregated titles
    # Find media where clean_title OR cntitle is in our set of search_titles
    candidates = db.query(models.TdbMedia).filter(
        and_(
            models.TdbMedia.clean_title == torinfo.clean_title,
            models.TdbMedia.tmdb_cat == torinfo.tmdb_cat,
            models.TdbMedia.cntitle == torinfo.cntitle
        )
    ).all()

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

def find_media_by_torname_regex(db: Session, title: str, clean_title: str) -> models.TdbMedia | None:
    all_media_with_regex = db.query(models.TdbMedia).filter(
        models.TdbMedia.torname_regex != None,
        # models.TdbMedia.clean_title.like(f"%{clean_title}%") # 加上后只能查到 clean_title 比库里的短的
    ).all()
    for media in all_media_with_regex:
        try:
            if re.search(media.torname_regex, title, re.IGNORECASE):
                logger.info(f"Found media by regex: {media.torname_regex} for title: {title}")
                return media
        except re.error:
            continue
    return None

def find_media_by_tmdb_id(db: Session, tmdb_cat: str, tmdb_id: int) -> models.TdbMedia | None:
    return db.query(models.TdbMedia).filter(models.TdbMedia.tmdb_cat == tmdb_cat, models.TdbMedia.tmdb_id == tmdb_id).first()

def find_media_by_imdb_id(db: Session, imdb_id: str) -> models.TdbMedia | None:
    return db.query(models.TdbMedia).filter(models.TdbMedia.imdb_id == imdb_id).first()


# --- Create Operations ---

def create_media(db: Session, media: schemas.TdbMediaCreate) -> models.TdbMedia:
    # logger.debug(f"Creating media with data: {media.model_dump_json(indent=2)}")
    if not media.tmdb_id:
        # Find the minimum tmdb_id that is less than 0
        min_id = db.query(func.min(models.TdbMedia.tmdb_id)).filter(models.TdbMedia.tmdb_id < 0).scalar()
        if min_id is None:
            media.tmdb_id = -1
        else:
            media.tmdb_id = min_id - 1

    db_media = models.TdbMedia(**media.model_dump())
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media

def _create_media_schema_from_torinfo(torinfo: TorrentInfo) -> schemas.TdbMediaCreate:
    """Helper function to create a TdbMediaCreate schema from a TorrentInfo object."""
    return schemas.TdbMediaCreate(
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
        tmdb_genres=torinfo.tmdb_genres, # Directly use the pre-formatted string
        id_score=torinfo.id_score,
        seasons=torinfo.seasons,
    )

def create_media_from_torinfo(db: Session, torinfo: TorrentInfo) -> models.TdbMedia:
    """Creates a media item from a TorrentInfo object and saves it to the database."""
    media_create = _create_media_schema_from_torinfo(torinfo)
    return create_media(db, media_create)

def create_torrent(db: Session, torinfo: TorrentInfo, media_id: int) -> models.TdbTorrent:
    torrent_create = schemas.TdbTorrentCreate(name=torinfo.torname, infolink=torinfo.infolink)
    db_torrent = models.TdbTorrent(**torrent_create.model_dump(), media_id=media_id)
    db.add(db_torrent)
    db.commit()
    db.refresh(db_torrent)
    return db_torrent

# --- Update Operations ---

def update_media(db: Session, media_id: int, media_update: schemas.TdbMediaUpdate) -> models.TdbMedia | None:
    db_media = get_media(db, media_id)
    if db_media:
        for key, value in media_update.model_dump(exclude_unset=True).items():
            setattr(db_media, key, value)
        db.commit()
        db.refresh(db_media)
    return db_media

# --- Delete Operations ---

def delete_media(db: Session, media_id: int) -> models.TdbMedia | None:
    db_media = get_media(db, media_id)
    if db_media:
        db.delete(db_media)
        db.commit()
    return db_media

def delete_torrent(db: Session, torrent_id: int) -> models.TdbTorrent | None:
    db_torrent = db.query(models.TdbTorrent).filter(models.TdbTorrent.id == torrent_id).first()
    if db_torrent:
        db.delete(db_torrent)
        db.commit()
    return db_torrent


def is_all_chinese(s: str) -> bool:
    """检查字符串是否主要由中文组成"""
    if not s:
        return False
    # 检查是否包含至少一个中文字符，并且排除掉纯数字或特殊字符的情况
    # \u4e00-\u9fff 是中文 Unicode 范围
    return any('\u4e00' <= char <= '\u9fff' for char in s)

def weak_title(torinfo: TorrentInfo) -> bool:
    if (torinfo.clean_title == torinfo.cntitle):
        if is_all_chinese(torinfo.clean_title) and len(torinfo.clean_title) < 5:
            return True
    return False


# --- Main Search Logic ---

def search_and_create_media(db: Session, torinfo: TorrentInfo, searcher: TMDbSearcher, override: bool = False) -> models.TdbMedia | schemas.TdbMedia | None:
    # Handle override: delete existing matching media entries before searching
    SCORE_LIMIT = 19

    if override:
        # Collect all titles that might match
        search_titles = {torinfo.clean_title, torinfo.cntitle, torinfo.extitle}
        search_titles = {title for title in search_titles if title}
        
        if search_titles:
            # Delete media entries matching these titles
            matching_media = db.query(models.TdbMedia).filter(
                or_(
                    models.TdbMedia.clean_title.in_(search_titles),
                    models.TdbMedia.cntitle.in_(search_titles)
                )
            ).all()
            
            for media in matching_media:
                logger.info(f"OVERRIDE: Deleting existing media: {media.tmdb_title} (clean_title: {media.clean_title}, cntitle: {media.cntitle})")
                # Delete associated torrents first
                db.query(models.TdbTorrent).filter(models.TdbTorrent.media_id == media.id).delete()
                # Delete the media entry
                db.delete(media)
            
            db.commit()

    # 1. TMDb ID provided
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

    if not override:
        # 2. Exact torrent name match
        if torrent := find_torrent_by_name(db, torinfo.torname):
            logger.info(f"LOCAL: Found existing torrent by name: {torinfo.torname}")
            return torrent.tdb_media

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

    if not override:
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

    # First try a raw TMDb search (same route as the frontend's /tmdb/search) to get a list
    # of candidate results that respect the provided year. This reduces mismatch between
    # frontend searches and backend blind searches.
    # Use TMDbSearcher helper to pick best raw result (aligns with frontend behavior)
    search_term = torinfo.extitle or torinfo.cntitle or torinfo.clean_title or torinfo.torname
    media_type = 'tv' if torinfo.season or torinfo.tmdb_cat == 'tv' else 'multi'
    chosen = None
    try:
        preferred_titles = [torinfo.extitle, torinfo.cntitle, torinfo.clean_title]
        chosen = searcher.pick_best_raw_result(search_term, year=torinfo.year, media_type=media_type, preferred_titles=preferred_titles)
    except Exception as e:
        logger.debug(f"pick_best_raw_result failed: {e}")

    if chosen:
        try:
            # Populate torinfo from the chosen candidate
            searcher.populate_torinfo_from_raw(torinfo, chosen)

            # Fetch full details to populate additional fields
            if searcher.search_tmdb_by_tmdbid(torinfo):
                if media := find_media_by_tmdb_id(db, torinfo.tmdb_cat, torinfo.tmdb_id):
                    logger.info(f"LOCAL: Found media by TMDb ID after blind search: {media.tmdb_title}")
                    create_torrent(db, torinfo, media.id)
                    return media

                logger.debug(f"score: {torinfo.id_score}")
                if (torinfo.id_score < SCORE_LIMIT) or weak_title(torinfo) :
                    logger.warning(f"BLIND id_score too low: {torinfo.id_score} for {torinfo.torname}")
                    media_data = _create_media_schema_from_torinfo(torinfo)
                    torrent_data = schemas.TdbTorrentCreate(name=torinfo.torname, infolink=torinfo.infolink)
                    response_media = schemas.TdbMedia(**media_data.model_dump())
                    response_media.torrents.append(schemas.TdbTorrent(**torrent_data.model_dump()))
                    return response_media

                logger.info(f"TMDb: Found media by blind search: {torinfo.tmdb_title}")
                new_media = create_media_from_torinfo(db, torinfo)
                create_torrent(db, torinfo, new_media.id)
                return new_media
        except Exception as e:
            logger.error(f"Error while using chosen raw TMDb result: {e}")

    # Fallback: try the existing blind search method which has more heuristics
    if searcher.search_tmdb(torinfo):
        if media := find_media_by_tmdb_id(db, torinfo.tmdb_cat, torinfo.tmdb_id):
            logger.info(f"LOCAL: Found media by TMDb ID after blind search: {media.tmdb_title}")
            create_torrent(db, torinfo, media.id)
            return media

        logger.debug(f"score: {torinfo.id_score}")
        if torinfo.id_score < SCORE_LIMIT or weak_title(torinfo):
            logger.warning(f"BLIND id_score too low: {torinfo.id_score} for {torinfo.torname}")
            media_data = _create_media_schema_from_torinfo(torinfo)
            torrent_data = schemas.TdbTorrentCreate(name=torinfo.torname, infolink=torinfo.infolink)
            response_media = schemas.TdbMedia(**media_data.model_dump())
            response_media.torrents.append(schemas.TdbTorrent(**torrent_data.model_dump()))
            return response_media

        logger.info(f"TMDb: Found media by blind search: {torinfo.tmdb_title}")
        new_media = create_media_from_torinfo(db, torinfo)
        create_torrent(db, torinfo, new_media.id)
        return new_media

    logger.warning(f"FAIL: Could not find any match for: {torinfo.torname}")
    return None