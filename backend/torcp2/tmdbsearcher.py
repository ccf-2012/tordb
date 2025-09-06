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

def contains_cjk(text):
    if not text: return False
    return re.search(r'[\u4e00-\u9fa5]', text)

def longest_common_subsequence_length(str1, str2):
    """
    计算两个字符串的最长公共子序列长度（动态规划实现）
    
    Args:
        str1 (str): 第一个字符串
        str2 (str): 第二个字符串
    
    Returns:
        int: 最长公共子序列的长度
    """
    m, n = len(str1), len(str2)
    
    # 创建二维dp数组，dp[i][j]表示str1前i个字符和str2前j个字符的LCS长度
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # 填充dp数组
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return dp[m][n]

def find_longest_consecutive_match(str1, str2):
    """
    找到两个字符串中最长的连续相同子串长度
    
    Args:
        str1 (str): 第一个字符串
        str2 (str): 第二个字符串
    
    Returns:
        tuple: (最长匹配长度, 在str1中的起始位置, 在str2中的起始位置)
    """
    max_length = 0
    best_pos1 = -1
    best_pos2 = -1
    
    for i in range(len(str1)):
        for j in range(len(str2)):
            length = 0
            # 从位置i和j开始比较连续字符
            while (i + length < len(str1) and 
                   j + length < len(str2) and 
                   str1[i + length] == str2[j + length]):
                length += 1
            
            if length > max_length:
                max_length = length
                best_pos1 = i
                best_pos2 = j
    
    return max_length, best_pos1, best_pos2


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
            torinfo.year = self._get_year_from_datestr(release_date)
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
                self._fill_tmdb_details(torinfo, details) # Pass details to avoid re-fetching
                return True

        except Exception as e:
            logger.error(f"Error searching TMDb by ID {torinfo.tmdb_id}: {e}")
        return False

    def search_by_imdb_id(self, torinfo):
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
                self._fill_tmdb_details(torinfo)
                return True
            elif results[other_results]:
                self._save_tmdb_result(torinfo, results[other_results][0])
                self._fill_tmdb_details(torinfo)
                return True
        except Exception as e:
            logger.error(f"Error searching TMDb by IMDb ID {torinfo.imdb_id}: {e}")
        
        return False

    def _perform_search(self, search_term, search_cat, year):
        search = Search()
        results = []
        stryear = str(year) if year else None

        logger.info(f'Searching for "{search_term}" in [{search_cat}] with year: {year or "any"}')

        try:
            if search_cat == 'tv':
                # no year for tv
                results = search.tv_shows(term=search_term, adult=True)
            elif search_cat == 'movie':
                results = search.movies(term=search_term, adult=True, year=stryear)
            else: # multi
                results = search.multi(term=search_term, adult=True, page=1) # year not supported in multi
        except Exception as e:
            logger.error(f"TMDb API search failed for '{search_term}': {e}")
            return None, None

        if not results:
            # TODO: search without year?
            return None, None

        result = self._find_year_match(results, year, strict=True)
        if result:
            return result, 'strict'

        result = self._find_year_match(results, year, strict=False)
        if result:
            return result, 'fuzzy'
            
        # No year match (or year was 0)
        if not year:
             return self._find_year_match(results, 0), 'any'

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

    def _search_tmdb(self, torinfo):
        torinfo.id_score = 0
        title = torinfo.clean_title
        cntitle = torinfo.cntitle
        extitle = torinfo.extitle
        intyear = self._fix_year(torinfo)

        # Title cleaning
        cuttitle = self._clean_title(title)
        if cntitle:
            torinfo.id_score += len(cntitle) * 2
        if title != cntitle:
            torinfo.id_score += len(title)
        if extitle and (extitle != cntitle) :
            torinfo.id_score += 8
        if intyear > 1900:
            torinfo.id_score += 10

        logger.debug(f"Search ==>  title: {title}, cntitle: {cntitle}, extitle: {extitle}, year:{intyear}  init id_score: {torinfo.id_score}")

        search_list = self._build_search_list(torinfo, cntitle, cuttitle, extitle)
        logger.debug(f"search list: {search_list}")
        for category, term in search_list:
            if not term:
                continue

            result, match_type = self._perform_search(term, category, intyear)
            if result:
                if category == 'multi':
                    self._save_tmdb_result(torinfo, result)
                else:
                    self._save_tmdb_result(torinfo, result, media_type=category)

                # if intyear > 1900 and match_type == 'strict':
                #     torinfo.id_score += 5
                if category != 'multi':
                    torinfo.id_score += 5

                if cntitle:
                    if cntitle == torinfo.tmdb_title:
                        torinfo.id_score += 10 + len(cntitle)
                    else:
                        # 找到的tmdb_title，与 cntitle 最长公共子序列长度，接近len(tmdb_title)
                        length = longest_common_subsequence_length(cntitle, torinfo.tmdb_title)
                        torinfo.id_score += 2 * length
                        # TODO：下面方案待定
                        # diff = 10 - 2 * abs(len(torinfo.tmdb_title) - len(cntitle))
                        # torinfo.id_score += diff
                self._fill_tmdb_details(torinfo)
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
        title = self._replace_roman_num(title)
        return title.strip()

    def _build_search_list(self, torinfo, cntitle, cuttitle, extitle):
        # Builds the list of searches to perform
        searches = []
        if torinfo.season:
            torinfo.id_score += 5
            searches = [('tv', cntitle), ('tv', cuttitle), ('multi', extitle), ('multi', cntitle)]
        elif torinfo.tmdb_cat == 'tv':
            torinfo.id_score += 5
            searches = [('tv', cntitle), ('multi', cuttitle), ('multi', extitle)]
        elif torinfo.tmdb_cat == 'movie':
            searches = [('movie', cntitle),  ('movie', cuttitle), ('movie', extitle), ('multi', cuttitle), ('multi', cntitle)]
        else:
            searches = [('multi', cntitle), ('multi', cuttitle), ('multi', extitle), ('tv', cuttitle), ('movie', cuttitle)]

        # 过滤掉搜索关键字为空的条目，并移除重复的条目
        unique_list = list(dict.fromkeys(item for item in searches if item[1]))

        if len(cntitle) < 3 and len(cuttitle) > 5:
            # 如果cntitle太短，则优先使用cuttitle
            return sorted(unique_list, key=lambda x: x[1] != cuttitle)
        return unique_list

    def search_tmdb(self, torinfo):
        try:
            return self._search_tmdb(torinfo)
        except Exception as e:
            logger.error(f"An unexpected error occurred during TMDb search: {e}", exc_info=True)
            return False

    # --- Utility Functions ---
    
    def _get_year_from_datestr(self, datestr):
        if not datestr: return 0
        m = re.search(r'\b(19\d{2}|20\d{2})\b', str(datestr))
        return tryint(m.group(1)) if m else 0

    def _get_title(self, result):
        return getattr(result, 'name', getattr(result, 'title', getattr(result, 'original_name', getattr(result, 'original_title', ''))))

    def _replace_roman_num(self, titlestr):
        roman_map = {'II': '2', 'III': '3', 'IV': '4', 'V': '5', 'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'XI': '11', 'XII': '12', 'XIII': '13', 'XIV': '14', 'XV': '15', 'XVI': '16'}
        for roman, arabic in roman_map.items():
            titlestr = re.sub(f'\\b{roman}\\b', arabic, titlestr, flags=re.IGNORECASE)
        return titlestr

    def _find_year_match(self, results, year, strict=True):
        matchList = []
        
        # Handle both list and dict from tmdbv3api
        resultlist = results if isinstance(results, list) else results.get('results', [])

        for result in resultlist:
            resyear = self._get_year_from_datestr(getattr(result, 'release_date', '') or getattr(result, 'first_air_date', ''))
            
            if year == 0:
                matchList.append(result)
                continue

            if strict:
                if resyear == year:
                    matchList.append(result)
            else: # fuzzy
                if resyear == 0:
                    matchList.append(result)
                elif resyear in [year - 1, year, year + 1]:
                    matchList.append(result)
                else:
                    return None
        
        
        if not matchList:
            return None

        # Prefer item with CJK title if language is Chinese
        if self.tmdb and self.tmdb.language == 'zh-CN':
            for item in matchList[:3]:
                if contains_cjk(self._get_title(item)):
                    return item
        
        return matchList[0]

    def _fix_year(self, torinfo):
        intyear = torinfo.year
        if not 1900 < intyear < 2100:
            intyear = 0
        
        # For TV shows, only trust the year if it's the first season
        if torinfo.season and 'S01' not in torinfo.season:
            intyear = 0
            
        return intyear

    def _get_imdb_info(self, torinfo):
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

    def _fill_tmdb_details(self, torinfo, details=None):
        logger.debug(f"Filling details for {torinfo.tmdb_cat}-{torinfo.tmdb_id}")
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

        # Fill in seasons details for TV shows
        if torinfo.tmdb_cat == 'tv' and hasattr(details, 'seasons'):
            seasons_data = []
            for season in details.seasons:
                seasons_data.append({
                    'season_number': getattr(season, 'season_number', None),
                    'air_date': getattr(season, 'air_date', None),
                    'episode_count': getattr(season, 'episode_count', None),
                    'name': getattr(season, 'name', None),
                    'overview': getattr(season, 'overview', None),
                    'poster_path': getattr(season, 'poster_path', None),
                })
            torinfo.seasons = seasons_data


