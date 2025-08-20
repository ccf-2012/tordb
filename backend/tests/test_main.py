
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# Add the parent directory to the Python path to find the `app` module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_db
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

client = TestClient(app)

# --- Fixture to clean up database after tests ---
@pytest.fixture(scope="function", autouse=True)
def cleanup_database():
    # Before each test, clean the tables
    for table in reversed(Base.metadata.sorted_tables):
        engine.execute(table.delete())
    yield
    # After each test, clean up again
    for table in reversed(Base.metadata.sorted_tables):
        engine.execute(table.delete())


# --- Tests ---
def test_read_all_media_empty():
    response = client.get("/api/media/")
    assert response.status_code == 200
    assert response.json()["items"] == []

def test_search_media_not_found():
    # This test assumes the torrent name won't be found and external search fails
    # It requires a valid (but not necessarily correct) TMDB API key in config
    response = client.get("/api/search?torname=ThisIsAFakeTorrentNameThatShouldNotExist123")
    # The API should return 404 if TMDb can't find a match
    assert response.status_code == 404
    assert "Could not find TMDb match" in response.json()["detail"]

def test_create_and_read_media():
    # 1. Create a new media item
    media_data = {
        "torname_regex": "test.movie.2023",
        "tmdb_id": 12345,
        "tmdb_title": "Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/poster.jpg"
    }
    response = client.post("/api/media/", json=media_data)
    assert response.status_code == 200
    created_media = response.json()
    assert created_media["tmdb_title"] == "Test Movie"
    assert "id" in created_media

    media_id = created_media["id"]

    # 2. Read the media item back
    response = client.get(f"/api/media/{media_id}")
    assert response.status_code == 200
    read_media = response.json()
    assert read_media["tmdb_id"] == 12345

    # 3. Read all media items
    response = client.get("/api/media/")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["tmdb_title"] == "Test Movie"

def test_create_torrent_for_media():
    # 1. First, create a media item to associate the torrent with
    media_data = {
        "torname_regex": "another.test.movie.2024",
        "tmdb_id": 54321,
        "tmdb_title": "Another Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/another_poster.jpg"
    }
    media_response = client.post("/api/media/", json=media_data)
    assert media_response.status_code == 200, media_response.json()
    media_id = media_response.json()["id"]

    # 2. Now, create a torrent for that media
    torrent_data = {"name": "Another.Test.Movie.2024.1080p.BluRay.x264.torrent"}
    response = client.post(f"/api/torrents/?media_id={media_id}", json=torrent_data)
    assert response.status_code == 200
    created_torrent = response.json()
    assert created_torrent["name"] == torrent_data["name"]
    assert created_torrent["media_id"] == media_id

    # 3. Verify the media item now has this torrent
    response = client.get(f"/api/media/{media_id}")
    assert len(response.json()["torrents"]) == 1
    assert response.json()["torrents"][0]["name"] == torrent_data["name"]

def test_search_existing_torrent():
    # 1. Create a media item
    media_data = {
        "torname_regex": "search.test.2025",
        "tmdb_id": 98765,
        "tmdb_title": "Search Test Movie",
        "tmdb_cat": "movie",
        "tmdb_poster": "/search_poster.jpg"
    }
    media_response = client.post("/api/media/", json=media_data)
    assert media_response.status_code == 200
    media_id = media_response.json()["id"]

    # 2. Create a torrent for that media
    torrent_name = "Search.Test.2025.1080p.mkv"
    torrent_data = {"name": torrent_name}
    client.post(f"/api/torrents/?media_id={media_id}", json=torrent_data)

    # 3. Search for the existing torrent
    response = client.get(f"/api/search?torname={torrent_name}")
    assert response.status_code == 200
    assert response.json()["tmdb_title"] == "Search Test Movie"

    # 4. Search for a new torrent that matches the regex
    new_torrent_name = "Search.Test.2025.720p.mp4"
    response = client.get(f"/api/search?torname={new_torrent_name}")
    assert response.status_code == 200
    assert response.json()["tmdb_title"] == "Search Test Movie"

    # 5. Verify that a new torrent was created
    response = client.get(f"/api/media/{media_id}")
    assert len(response.json()["torrents"]) == 2

