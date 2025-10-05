from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, JSON, Text, Float
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from .config import settings

DATABASE_URL = settings.get_database_url()

# For mysql, no need check_same_thread
if settings.db_type == 'mysql':
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TdbMedia(Base):
    __tablename__ = "tdb_media"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    torname_regex = Column(String(255), index=True, nullable=True)
    clean_title = Column(String(255), index=True, nullable=False)
    cntitle = Column(String(255), nullable=True)
    tmdb_id = Column(Integer, index=True, nullable=True)
    imdb_id = Column(String(32), index=True, nullable=True)
    tmdb_title = Column(String(255), nullable=True)
    tmdb_cat = Column(String(10), nullable=True)
    tmdb_poster = Column(String(255), nullable=True)
    tmdb_year = Column(Integer, nullable=True)
    tmdb_genres = Column(String(255), nullable=True)
    tmdb_overview = Column(Text, nullable=True)
    tmdb_backdrop = Column(String(255), nullable=True)
    tmdb_runtime = Column(Integer, nullable=True)
    tmdb_popularity = Column(Float, nullable=True)
    tmdb_vote_average = Column(Float, nullable=True)
    tmdb_vote_count = Column(Integer, nullable=True)
    tmdb_casts = Column(JSON, nullable=True)
    original_language = Column(String(32), nullable=True)
    release_air_date = Column(String(32), nullable=True)
    origin_country = Column(String(32), nullable=True)
    original_title = Column(String(255), nullable=True)
    production_countries = Column(String(32), nullable=True)
    custom_title = Column(String(255), nullable=True)
    custom_path = Column(String(255), nullable=True)
    id_score = Column(Integer, nullable=True)
    seasons = Column(JSON, nullable=True)

    torrents = relationship("TdbTorrent", back_populates="tdb_media", cascade="all, delete-orphan")

class TdbTorrent(Base):
    __tablename__ = "tdb_torrents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False)
    infolink = Column(String(255), nullable=True)
    subtitle = Column(String(200), nullable=True)
    media_id = Column(Integer, ForeignKey("tdb_media.id"), nullable=False)

    tdb_media = relationship("TdbMedia", back_populates="torrents")

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
