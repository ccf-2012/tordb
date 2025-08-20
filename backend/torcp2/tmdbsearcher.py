from tmdbv3api import TMDb, Movie, TV, Search, Find
from imdb import Cinemagoer
import re
import time
from loguru import logger

def tryint(instr):
    try:
        return int(instr)
    except (ValueError, TypeError):
        return 0

class TMDbSearcher:
    def __init__(self, tmdb_api_key, tmdb_lang='zh-CN'):
        if tmdb_api_key:
            self.tmdb = TMDb()
            self.tmdb.api_key = tmdb_api_key
            self.tmdb.language = tmdb_lang
        else:
            self.tmdb = None

    def _save_tmdb_result(self, torinfo, result, media_type=None):
        if not result:
            logger.info(f'No result to save for: {torinfo.media_title}')
            return False

        torinfo.tmdb_id = result.id
        torinfo.tmdb_cat = media_type or getattr(result, 'media_type', 'movie')

        if torinfo.tmdb_cat == 'tv':
            torinfo.tmdb_title = getattr(result, 'name', getattr(result, 'original_name', ''))
            date_attr = 'first_air_date'
        else: # movie or other
            torinfo.tmdb_title = getattr(result, 'title', getattr(result, 'original_title', ''))
            date_attr = 'release_date'

        if hasattr(result, 'original_language'):
            torinfo.original_language = 'cn' if result.original_language == 'zh' else result.original_language
        
        torinfo.popularity = getattr(result, 'popularity', 0)
        torinfo.poster_path = getattr(result, 'poster_path', '')
        
        release_date = getattr(result, date_attr, None)
        if not release_date and date_attr == 'release_date': # fallback for movies
             release_date = getattr(result, 'first_air_date', None)

        if release_date:
            torinfo.year = self.getYear(release_date)
            torinfo.release_air_date = release_date
        else:
            torinfo.year = 0

        torinfo.genre_ids = getattr(result, 'genre_ids', [])
        if hasattr(result, 'genres'):
             torinfo.genre_ids = [g['id'] for g in result.genres]
        if hasattr(result, 'overview'):
            torinfo.overview = result.overview or ''

        logger.success(f'Found [{torinfo.tmdb_cat}-{torinfo.tmdb_id}]: {torinfo.tmdb_title}')
        return True

    def search_tmdb_by_tmdbid(self, torinfo):
        """Fetches details by TMDb ID and populates torinfo."""
        if not torinfo.tmdb_id or not torinfo.tmdb_cat:
            logger.error("TMDb ID or category missing for TMDb search.")
            return False
        try:
            details = None
            if torinfo.tmdb_cat == 'tv':
                details = TV().details(torinfo.tmdb_id)
            elif torinfo.tmdb_cat == 'movie':
                details = Movie().details(torinfo.tmdb_id)

            if details:
                # Overwrite torinfo with full details
                self._save_tmdb_result(torinfo, details, torinfo.tmdb_cat)
                self.fillTMDbDetails(torinfo, details) # Pass details to avoid re-fetching
                return True

        except Exception as e:
            logger.error(f"Error searching TMDb by ID {torinfo.tmdb_id}: {e}")
        return False

    def searchTMDbByIMDbId(self, torinfo):
        if not torinfo.imdb_id.startswith('tt'):
            logger.error(f"Invalid IMDb ID: {torinfo.imdb_id}")
            return False
        try:
            find = Find()
            results = find.find_by_imdb_id(imdb_id=torinfo.imdb_id)
            
            # Prefer the category if it's already known
            preferred_results = 'tv_results' if torinfo.tmdb_cat == 'tv' else 'movie_results'
            other_results = 'movie_results' if torinfo.tmdb_cat == 'tv' else 'tv_results'

            if results[preferred_results]:
                self._save_tmdb_result(torinfo, results[preferred_results][0])
                self.fillTMDbDetails(torinfo)
                return True
            elif results[other_results]:
                self._save_tmdb_result(torinfo, results[other_results][0])
                self.fillTMDbDetails(torinfo)
                return True
        except Exception as e:
            logger.error(f"Error searching TMDb by IMDb ID {torinfo.imdb_id}: {e}")
        
        return False

    def _perform_search(self, search_term, search_cat, year, stryear):
        search = Search()
        results = []
        
        logger.info(f'Searching for "{search_term}" in [{search_cat}] with year: {year or "any"}')

        try:
            if search_cat == 'tv':
                results = search.tv_shows(term=search_term, adult=True, release_year=stryear)
            elif search_cat == 'movie':
                results = search.movies(term=search_term, adult=True, year=stryear)
            else: # multi
                results = search.multi(term=search_term, adult=True, page=1) # year not supported in multi
        except Exception as e:
            logger.error(f"TMDb API search failed for '{search_term}': {e}")
            return None, None

        if not results:
            return None, None

        # Strict year match
        result = self.findYearMatch(results, year, strict=True)
        if result:
            return result, 'strict'

        # Fuzzy year match
        result = self.findYearMatch(results, year, strict=False)
        if result:
            return result, 'fuzzy'
            
        # No year match (or year was 0)
        if not year:
             return self.findYearMatch(results, 0), 'any'

        return None, None

    def _generate_cntitle2(self, cntitle):
        """Generates a secondary search title (cntitle2) from a Chinese title."""
        if not cntitle:
            return ''
        # Case 1: Subtitle after '：'
        if '：' in cntitle:
            parts = cntitle.split('：', 1)
            if len(parts) > 1:
                return parts[1].strip()
        # Case 2: 普契尼《托斯卡》
        if '《' in cntitle:
            return cntitle.split('《', 1)[1].split('》')[0]
        # Case 3: Title with trailing numbers like "中文123"
        match = re.match(r'^(.+?)(\d+)', cntitle)
        if match:
            return match.group(1).strip()
        # Case 4:  攻壳机动队真人版, 阿拉丁真人版
        if '真人版' in cntitle:
            return cntitle.split('真人版')[0]

        return ''

    def _searchTMDb(self, torinfo):
        torinfo.confidence = 0
        title = torinfo.media_title
        cntitle = torinfo.subtitle
        stryear, intyear = self.fixYear(torinfo)

        # Title cleaning
        cuttitle = self._clean_title(title)
        # Category detection
        if 'the movie' in cuttitle.lower():
            torinfo.tmdb_cat = 'movie'
            torinfo.confidence += 5

        cntitle2 = ''
        if cntitle:
            cntitle = self._clean_title(cntitle)
            cntitle2 = self._generate_cntitle2(cntitle)
        
        torinfo.confidence += len(cuttitle)
        if cntitle:
            torinfo.confidence += 10


        search_list = self._build_search_list(torinfo, cntitle, cuttitle, cntitle2)

        for category, term in search_list:
            if not term:
                continue

            result, match_type = self._perform_search(term, category, intyear, stryear)

            if result:
                if category == 'multi':
                    self._save_tmdb_result(torinfo, result)
                else:
                    self._save_tmdb_result(torinfo, result, media_type=category)
                
                # Update confidence
                if match_type == 'strict':
                    torinfo.confidence += 20
                elif match_type == 'fuzzy':
                    torinfo.confidence += 10
                if category != 'multi':
                    torinfo.confidence += 5
                
                self.fillTMDbDetails(torinfo)
                return True

        logger.warning(f'TMDb Not found: [{title}] [{cntitle}]')
        return False

    def _clean_title(self, title):
        # A helper to consolidate title cleaning regex
        title = re.sub(r'^(Jade|\w{2,3}TV)\s+', '', title, flags=re.I)
        title = re.sub(r'\b(Extended|Anthology|Trilogy|Quadrilogy|Tetralogy|Collections?)\s*$', '', title, flags=re.I)
        title = re.sub(r'\b(HD|S\d+|E\d+|V\d+|4K|DVD|CORRECTED|UnCut|SP)\s*$', '', title, flags=re.I)
        title = re.sub(r'^\s*(剧集|BBC：?|TLOTR|Jade|Documentary|【[^】]*】)', '', title, flags=re.I)
        title = re.sub(r'(\d+部曲|全\d+集.*|原盘|系列|\s[^\s]*压制.*)\s*$', '', title, flags=re.I)
        title = re.sub(r'(\b国粤双语|[\b\(]?\w+版|\b\d+集全).*$', '', title, flags=re.I)
        title = re.sub(r'(The[\s\.]*(Complete\w*|Drama\w*|Animate\w*)?[\s\.]*Series|The\s*Movie)\s*$', '', title, flags=re.I)
        title = re.sub(r'\b(Season\s?\d+)\b', '', title, flags=re.I)
        title = self.replaceRomanNum(title)
        return title.strip()

    def _build_search_list(self, torinfo, cntitle, cuttitle, cntitle2):
        # Builds the list of searches to perform
        searches = []
        if torinfo.season:
            torinfo.confidence += 10
            searches = [('tv', cntitle), ('tv', cuttitle), ('multi', cntitle), ('multi', cntitle2)]
        elif torinfo.tmdb_cat == 'tv':
            torinfo.confidence += 5
            searches = [('tv', cntitle), ('multi', cuttitle), ('multi', cntitle2)]
        elif torinfo.tmdb_cat == 'movie':
            torinfo.confidence += 5
            searches = [('movie', cntitle),  ('movie', cuttitle), ('movie', cntitle2), ('multi', cntitle), ('multi', cuttitle)]
        else:
            searches = [('multi', cntitle), ('multi', cuttitle), ('multi', cntitle2), ('tv', cuttitle), ('movie', cuttitle)]

        # 过滤掉搜索关键字为空的条目，并移除重复的条目
        unique_list = list(dict.fromkeys(item for item in searches if item[1]))

        if len(cntitle) < 3 and len(cuttitle) > 5:
            # 如果cntitle太短，则优先使用cuttitle
            return sorted(unique_list, key=lambda x: x[1] != cuttitle)
        return unique_list

    def searchTMDb(self, torinfo):
        try:
            return self._searchTMDb(torinfo)
        except Exception as e:
            logger.error(f"An unexpected error occurred during TMDb search: {e}", exc_info=True)
            return False

    # --- Utility Functions ---
    
    def getYear(self, datestr):
        if not datestr: return 0
        m = re.search(r'\b(19\d{2}|20\d{2})\b', str(datestr))
        return tryint(m.group(1)) if m else 0

    def getTitle(self, result):
        return getattr(result, 'name', getattr(result, 'title', getattr(result, 'original_name', getattr(result, 'original_title', ''))))

    def containsCJK(self, text):
        if not text: return False
        return re.search(r'[\u4e00-\u9fa5]', text)

    def replaceRomanNum(self, titlestr):
        roman_map = {'II': '2', 'III': '3', 'IV': '4', 'V': '5', 'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15', 'XVI': '16'}
        for roman, arabic in roman_map.items():
            titlestr = re.sub(f'\\b{roman}\\b', arabic, titlestr, flags=re.IGNORECASE)
        return titlestr

    def findYearMatch(self, results, year, strict=True):
        matchList = []
        
        # Handle both list and dict from tmdbv3api
        resultlist = results if isinstance(results, list) else results.get('results', [])

        for result in resultlist:
            resyear = self.getYear(getattr(result, 'release_date', '') or getattr(result, 'first_air_date', ''))
            
            if year == 0:
                matchList.append(result)
                continue

            if strict:
                if resyear == year:
                    matchList.append(result)
            else: # fuzzy
                if resyear in [year - 1, year, year + 1]:
                    matchList.append(result)
        
        if not matchList:
            return None

        # Prefer item with CJK title if language is Chinese
        if self.tmdb and self.tmdb.language == 'zh-CN':
            for item in matchList[:3]:
                if self.containsCJK(self.getTitle(item)):
                    return item
        
        return matchList[0]

    def fixYear(self, torinfo):
        intyear = torinfo.year
        if not 1900 < intyear < 2100:
            intyear = 0
        
        # For TV shows, only trust the year if it's the first season
        if torinfo.season and 'S01' not in torinfo.season:
            intyear = 0
            
        return str(intyear) if intyear else None, intyear

    def getIMDbInfo(self, torinfo):
        if not torinfo.imdb_id or not torinfo.imdb_id.startswith('tt'):
            logger.error(f"Invalid IMDb ID provided: {torinfo.imdb_id}")
            return ''
        
        ia = Cinemagoer()
        try:
            movie_id = torinfo.imdb_id[2:]
            movie = ia.get_movie(movie_id)
            torinfo.imdb_val = movie.get('rating')
            
            if movie.get('kind') == 'episode':
                series_id = 'tt' + movie.get('episode of').movieID
                logger.warning(f"Provided IMDb ID {torinfo.imdb_id} is an episode. Using series ID {series_id} instead.")
                torinfo.imdb_id = series_id
        except Exception as e:
            logger.error(f"Error getting IMDb info for {torinfo.imdb_id}: {e}")
        
        return torinfo.imdb_id

    def fillTMDbDetails(self, torinfo, details=None):
        if not torinfo.tmdb_id:
            return torinfo

        # If details are not passed in, fetch them
        if not details:
            if torinfo.tmdbDetails:  # Already filled
                details = torinfo.tmdbDetails
            else:
                try:
                    if torinfo.tmdb_cat == 'movie':
                        details = Movie().details(torinfo.tmdb_id)
                    elif torinfo.tmdb_cat == 'tv':
                        details = TV().details(torinfo.tmdb_id)
                    else:
                        return torinfo  # Cannot fetch details without a category
                except Exception as e:
                    logger.error(f"Failed to fetch TMDb details for {torinfo.tmdb_cat}-{torinfo.tmdb_id}: {e}")
                    return torinfo

        if not details:
            return torinfo

        torinfo.tmdbDetails = details

        # Fill in additional details
        if hasattr(details, 'origin_country') and details.origin_country:
            torinfo.origin_country = details.origin_country[0]
        torinfo.original_title = getattr(details, 'original_title', '')
        torinfo.overview = getattr(details, 'overview', '')
        torinfo.vote_average = getattr(details, 'vote_average', 0)
        if hasattr(details, 'production_countries') and details.production_countries:
            torinfo.production_countries = details.production_countries[0].get('iso_3166_1', '')