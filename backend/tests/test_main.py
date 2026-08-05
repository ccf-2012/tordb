import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# Add the parent directory to the Python path to find the `app` module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_db, verify_api_key
from app.models import Base

# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the test database and tables before tests run
Base.metadata.create_all(bind=engine)

# --- Dependency Override ---
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the dependency override to the app
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[verify_api_key] = lambda: None

client = TestClient(app)

# --- Fixture to clean up database after tests ---
@pytest.fixture(scope="function", autouse=True)
def cleanup_database():
    # Before each test, clean the tables
    with TestingSessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    yield
    # After each test, clean up again
    with TestingSessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()


# --- Tests ---
def test_read_all_media_empty():
    response = client.get("/api/tdb_media/")
    assert response.status_code == 200
    assert response.json()["items"] == []

def test_search_media_not_found():
    # This test assumes the torrent name won't be found and external search fails
    # It requires a valid (but not necessarily correct) TMDB API key in config
    query_data = {"torname": "ThisIsAFakeTorrentNameThatShouldNotExist123"}
    response = client.post("/api/query", json=query_data)
    assert response.status_code == 404
    assert "Could not find or create a media match" in response.json()["detail"]

def test_create_and_read_media():
    # 1. Create a new media item
    media_data = {
        "clean_title": "Test Movie",
        "torname_regex": "test.movie.2023",
        "tmdb_id": 12345,
        "tmdb_title": "Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/poster.jpg"
    }
    response = client.post("/api/tdb_media/", json=media_data)
    assert response.status_code == 200
    created_media = response.json()
    assert created_media["tmdb_title"] == "Test Movie"
    assert "id" in created_media

    media_id = created_media["id"]

    # 2. Read the media item back
    response = client.get(f"/api/tdb_media/{media_id}")
    assert response.status_code == 200
    read_media = response.json()
    assert read_media["tmdb_id"] == 12345

    # 3. Read all media items
    response = client.get("/api/tdb_media/")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["tmdb_title"] == "Test Movie"

def test_create_torrent_for_media():
    # 1. First, create a media item to associate the torrent with
    media_data = {
        "clean_title": "Another Test Movie",
        "torname_regex": "another.test.movie.2024",
        "tmdb_id": 54321,
        "tmdb_title": "Another Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/another_poster.jpg"
    }
    media_response = client.post("/api/tdb_media/", json=media_data)
    assert media_response.status_code == 200, media_response.json()
    media_id = media_response.json()["id"]

    # 2. Now, create a torrent for that media
    torrent_data = {"name": "Another.Test.Movie.2024.1080p.BluRay.x264.torrent"}
    response = client.post(f"/api/tdb_torrents/?media_id={media_id}", json=torrent_data)
    assert response.status_code == 200
    created_torrent = response.json()
    assert created_torrent["name"] == torrent_data["name"]
    assert created_torrent["media_id"] == media_id

    # 3. Verify the media item now has this torrent
    response = client.get(f"/api/tdb_media/{media_id}")
    assert len(response.json()["torrents"]) == 1
    assert response.json()["torrents"][0]["name"] == torrent_data["name"]

def test_search_existing_torrent():
    # 1. Create a media item
    media_data = {
        "clean_title": "Search Test Movie",
        "torname_regex": "search.test.2025",
        "tmdb_id": 98765,
        "tmdb_title": "Search Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/search_poster.jpg"
    }
    media_response = client.post("/api/tdb_media/", json=media_data)
    assert media_response.status_code == 200
    media_id = media_response.json()["id"]

    # 2. Create a torrent for that media
    torrent_name = "Search.Test.2025.1080p.mkv"
    torrent_data = {"name": torrent_name}
    client.post(f"/api/tdb_torrents/?media_id={media_id}", json=torrent_data)

    # 3. Search for the existing torrent
    query_data = {"torname": torrent_name}
    response = client.post("/api/query", json=query_data)
    assert response.status_code == 200
    assert response.json()["tmdb_title"] == "Search Test Movie"

    # 4. Search for a new torrent that matches the regex
    new_torrent_name = "Search.Test.2025.720p.mp4"
    query_data = {"torname": new_torrent_name}
    response = client.post("/api/query", json=query_data)
    assert response.status_code == 200
    assert response.json()["tmdb_title"] == "Search Test Movie"

    # 5. Verify that a new torrent was created
    response = client.get(f"/api/tdb_media/{media_id}")
    assert len(response.json()["torrents"]) == 2

def test_override_does_not_delete_custom_media():
    # 1. Create a custom media item (no tmdb_id provided, gets assigned negative tmdb_id)
    custom_media_data = {
        "clean_title": "Custom Test Movie",
        "cntitle": "自定义测试电影",
        "tmdb_title": "Custom Test Movie Title",
        "tmdb_cat": "movie"
    }
    response = client.post("/api/tdb_media/", json=custom_media_data)
    assert response.status_code == 200
    custom_media = response.json()
    custom_id = custom_media["id"]
    assert custom_media["tmdb_id"] < 0

    # 2. Trigger override query for the same title
    from app import crud, models
    from torcp2.torinfo import TorrentInfo
    from unittest.mock import MagicMock

    torinfo = TorrentInfo()
    torinfo.clean_title = "Custom Test Movie"
    torinfo.cntitle = "自定义测试电影"
    searcher = MagicMock()
    searcher.search_tmdb_by_tmdbid.return_value = False
    searcher.search_by_imdb_id.return_value = False
    searcher.search_tmdb.return_value = False
    searcher.pick_best_raw_result.return_value = None

    with TestingSessionLocal() as db:
        crud.search_and_create_media(db, torinfo, searcher, override=True)
        # Check custom media still exists
        preserved = db.query(models.TdbMedia).filter(models.TdbMedia.id == custom_id).first()
        assert preserved is not None
        assert preserved.clean_title == "Custom Test Movie"

def test_override_deletes_standard_media_but_preserves_custom_media():
    # 1. Create a custom media item
    custom_response = client.post("/api/tdb_media/", json={
        "clean_title": "Shared Title",
        "cntitle": "共享标题",
        "tmdb_title": "Custom Title Entry",
        "tmdb_cat": "movie"
    })
    custom_id = custom_response.json()["id"]

    # 2. Create a standard media item (positive tmdb_id)
    standard_response = client.post("/api/tdb_media/", json={
        "clean_title": "Shared Title",
        "cntitle": "共享标题",
        "tmdb_id": 999888,
        "tmdb_title": "Standard TMDb Entry",
        "tmdb_cat": "movie"
    })
    standard_id = standard_response.json()["id"]

    from app import crud, models
    from torcp2.torinfo import TorrentInfo
    from unittest.mock import MagicMock

    torinfo = TorrentInfo()
    torinfo.clean_title = "Shared Title"
    torinfo.cntitle = "共享标题"
    searcher = MagicMock()
    searcher.search_tmdb_by_tmdbid.return_value = False
    searcher.search_by_imdb_id.return_value = False
    searcher.search_tmdb.return_value = False
    searcher.pick_best_raw_result.return_value = None

    with TestingSessionLocal() as db:
        crud.search_and_create_media(db, torinfo, searcher, override=True)

        # Custom entry should NOT be deleted
        assert db.query(models.TdbMedia).filter(models.TdbMedia.id == custom_id).first() is not None

        # Standard entry SHOULD be deleted
        assert db.query(models.TdbMedia).filter(models.TdbMedia.id == standard_id).first() is None


