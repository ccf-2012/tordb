from typing import List, Dict, Any
from torcp2.torinfo import TorrentInfo

def format_genres(torinfo: TorrentInfo) -> str:
    """
    Extracts and formats genre names from a TorrentInfo object into a comma-separated string.
    Prioritizes tmdbDetails['genres'] if available, otherwise uses genre_ids.
    """
    genres_list: List[Dict[str, Any]] = []
    if torinfo.tmdbDetails and "genres" in torinfo.tmdbDetails:
        genres_list = torinfo.tmdbDetails["genres"]
    elif torinfo.genre_ids:
        genres_list = [{"name": g} for g in torinfo.genre_ids]

    return ", ".join([genre["name"] for genre in genres_list])
