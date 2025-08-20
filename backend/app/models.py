from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///./tmdb_media.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    torname_regex = Column(String, index=True, nullable=False)
    tmdb_id = Column(Integer, index=True, nullable=True)
    imdb_id = Column(String, index=True, nullable=True)
    tmdb_title = Column(String, nullable=True)
    tmdb_cat = Column(String, nullable=True)
    tmdb_poster = Column(String, nullable=True)
    tmdb_year = Column(Integer, nullable=True)
    tmdb_genres = Column(String, nullable=True)
    tmdb_overview = Column(String, nullable=True)
    original_language = Column(String, nullable=True)
    release_air_date = Column(String, nullable=True)
    origin_country = Column(String, nullable=True)
    original_title = Column(String, nullable=True)
    production_countries = Column(String, nullable=True)
    custom_title = Column(String, nullable=True)
    custom_path = Column(String, nullable=True)

    torrents = relationship("Torrent", back_populates="media", cascade="all, delete-orphan")

class Torrent(Base):
    __tablename__ = "torrents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    infolink = Column(String, nullable=True)
    subtitle = Column(String(200), nullable=True)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=False)

    media = relationship("Media", back_populates="torrents")

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)