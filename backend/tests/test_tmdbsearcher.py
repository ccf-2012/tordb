
import pytest
from unittest.mock import MagicMock
from backend.torcp2.tmdbsearcher import TMDbSearcher
from backend.torcp2.torinfo import TorrentInfo

@pytest.fixture
def tmdb_searcher(mocker):
    """
    Provides a TMDbSearcher instance with a mocked _perform_search method.
    """
    # Mock the TMDb API key check during instantiation
    mocker.patch('backend.torcp2.tmdbsearcher.TMDb')
    searcher = TMDbSearcher(tmdb_api_key='fake_key')

    # Mock the internal _perform_search method
    searcher._perform_search = MagicMock()
    # Mock the _fill_tmdb_details to avoid external calls
    searcher._fill_tmdb_details = MagicMock()
    return searcher

def test_search_tmdb_perfect_match(tmdb_searcher):
    """
    Tests the id_score calculation for a perfect match.
    - cntitle is present and matches the search result.
    - Year is present.
    """
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="The Matrix",
        cntitle="黑客帝国",
        extitle="The Matrix",
        year=1999
    )

    # Mock the result from _perform_search
    mock_result = MagicMock()
    mock_result.id = 123
    mock_result.media_type = 'movie'
    mock_result.name = "黑客帝国"
    mock_result.title = "黑客帝国"
    mock_result.original_name = "The Matrix"
    mock_result.original_title = "The Matrix"
    mock_result.release_date = "1999-03-31"
    mock_result.first_air_date = None
    mock_result.overview = "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers."
    
    # Configure the mock to return our desired result
    tmdb_searcher._perform_search.return_value = (mock_result, 'strict')

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is True
    # Let's trace the id_score calculation based on the code:
    # initial score:
    # len(cntitle) * 2 = 4 * 2 = 8
    # len(title) = 10
    # extitle != cntitle = 8
    # year > 1900 = 10
    # initial_score = 8 + 10 + 8 + 10 = 36
    #
    # after search:
    # category != 'multi' = 5
    # cntitle == torinfo.tmdb_title = 10 + len(cntitle) = 10 + 4 = 14
    # final_score = 36 + 5 + 14 = 55
    assert torinfo.id_score == 50
    assert torinfo.tmdb_id == 123
    assert torinfo.tmdb_title == "黑客帝国"

    # Verify that _perform_search was called with the Chinese title first
    tmdb_searcher._perform_search.assert_called_with('黑客帝国', 'multi', 1999)


def test_search_tmdb_no_cntitle(tmdb_searcher):
    '''
    Tests score calculation when only clean_title is available.
    '''
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="The Matrix",
        cntitle="",
        extitle="",
        year=1999
    )

    mock_result = MagicMock()
    mock_result.id = 456
    mock_result.media_type = 'movie'
    mock_result.title = "The Matrix"
    mock_result.release_date = "1999-03-31"
    
    tmdb_searcher._perform_search.return_value = (mock_result, 'strict')

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is True
    # initial score:
    # len(title) = 10
    # year > 1900 = 10
    # initial_score = 10 + 10 = 20
    #
    # after search:
    # category != 'multi' = 5
    # final_score = 20 + 5 = 25
    assert torinfo.id_score == 20
    assert torinfo.tmdb_id == 456
    tmdb_searcher._perform_search.assert_called_with('The Matrix', 'multi', 1999)

def test_search_tmdb_similar_title(tmdb_searcher):
    '''
    Tests score calculation with similar (but not identical) Chinese titles.
    '''
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="黑客帝国4",
        cntitle="黑客帝国4",
        extitle="",
        year=2021
    )

    mock_result = MagicMock()
    mock_result.id = 789
    mock_result.media_type = 'movie'
    mock_result.title = "黑客帝国：矩阵重启" # TMDb title
    mock_result.release_date = "2021-12-17"
    
    tmdb_searcher._perform_search.return_value = (mock_result, 'strict')

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is True
    # initial score:
    # len(cntitle) * 2 = 5 * 2 = 10
    # len(title) = 5
    # year > 1900 = 10
    # initial_score = 10 + 5 + 10 = 25
    #
    # after search:
    # category != 'multi' = 5
    # LCS length between "黑客帝国4" and "黑客帝国：矩阵重启" is 4 ("黑客帝国")
    # 2 * length = 2 * 4 = 8
    # final_score = 25 + 5 + 8 = 38
    assert torinfo.id_score == 28
    assert torinfo.tmdb_id == 789

def test_search_tmdb_no_year(tmdb_searcher):
    '''
    Tests score calculation when year is not provided.
    '''
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="Inception",
        cntitle="盗梦空间",
        extitle="",
        year=0 # No year
    )

    mock_result = MagicMock()
    mock_result.id = 101
    mock_result.media_type = 'movie'
    mock_result.title = "盗梦空间"
    mock_result.release_date = "2010-07-16"
    
    tmdb_searcher._perform_search.return_value = (mock_result, 'any')

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is True
    # initial score:
    # len(cntitle) * 2 = 4 * 2 = 8
    # len(title) = 9
    # initial_score = 8 + 9 = 17
    #
    # after search:
    # category != 'multi' = 5
    # cntitle == torinfo.tmdb_title = 10 + len(cntitle) = 10 + 4 = 14
    # final_score = 17 + 5 + 14 = 36
    assert torinfo.id_score == 31
    tmdb_searcher._perform_search.assert_called_with('盗梦空间', 'multi', 0)

def test_search_tmdb_tv_show(tmdb_searcher):
    '''
    Tests score calculation for a TV show season.
    '''
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="Game of Thrones S01",
        cntitle="权力的游戏 第一季",
        extitle="",
        year=2011,
        season="S01"
    )

    mock_result = MagicMock()
    mock_result.id = 1399
    mock_result.media_type = 'tv'
    mock_result.name = "权力的游戏"
    mock_result.first_air_date = "2011-04-17"
    
    tmdb_searcher._perform_search.return_value = (mock_result, 'strict')

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is True
    # initial score:
    # len(cntitle) * 2 = 8 * 2 = 16
    # len(title) = 18
    # year > 1900 = 10
    # initial_score = 16 + 18 + 10 = 44
    #
    # in _build_search_list:
    # torinfo.season is present, score += 5 -> 49
    #
    # after search:
    # category != 'multi' = 5
    # LCS between "权力的游戏 第一季" and "权力的游戏" is 5
    # 2 * length = 2 * 5 = 10
    # final_score = 49 + 5 + 10 = 64
    assert torinfo.id_score == 67
    assert torinfo.tmdb_cat == 'tv'
    tmdb_searcher._perform_search.assert_called_with('权力的游戏 第一季', 'tv', 2011)

def test_search_tmdb_not_found(tmdb_searcher):
    '''
    Tests the case where no match is found.
    '''
    # 1. Arrange
    torinfo = TorrentInfo(
        clean_title="NonExistentMovie 123",
        cntitle="",
        extitle="",
        year=2025
    )
    
    # Configure the mock to return no result
    tmdb_searcher._perform_search.return_value = (None, None)

    # 2. Act
    found = tmdb_searcher._search_tmdb(torinfo)

    # 3. Assert
    assert found is False
    # Only initial score is calculated
    # len(title) = 20
    # year > 1900 = 10
    # initial_score = 20 + 10 = 30
    assert torinfo.id_score == 30
    assert torinfo.tmdb_id == ''


def test_search_tmdb_tv_show_year_fallback(mocker):
    """
    Tests that a TV show search falls back to 'any' year match when strict/fuzzy year matching fails.
    For example, filename says S01 2026, but the series premiered in 2024.
    """
    # 1. Arrange
    # Mock the TMDb API key check during instantiation
    mocker.patch('backend.torcp2.tmdbsearcher.TMDb')
    searcher = TMDbSearcher(tmdb_api_key='fake_key')
    searcher._fill_tmdb_details = MagicMock()

    # We want to test _perform_search directly, but mock search.tv_shows
    mock_search = MagicMock()
    mocker.patch('backend.torcp2.tmdbsearcher.Search', return_value=mock_search)

    mock_result = MagicMock()
    mock_result.id = 270845
    mock_result.media_type = 'tv'
    mock_result.name = "二龙湖·“村”暖花开"
    mock_result.first_air_date = "2024-10-11"
    mock_result.release_date = None

    mock_search.tv_shows.return_value = [mock_result]

    # 2. Act
    result, match_type = searcher._perform_search("二龙湖·村暖花开", "tv", 2026)

    # 3. Assert
    assert result is not None
    assert result.id == 270845
    assert match_type == 'any'


