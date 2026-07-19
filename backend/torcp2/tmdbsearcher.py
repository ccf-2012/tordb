from tmdbv3api import TMDb, Movie, TV, Search, Find
from imdb import Cinemagoer
import re
import time
import itertools
from types import SimpleNamespace
from loguru import logger
import requests

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
            # Create a new session with a timeout
            session = requests.Session()
            session.timeout = 30  # Set a 30-second timeout for all requests
            self.tmdb.session = session
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
        # if not torinfo.clean_title:
        #     torinfo.clean_title = torinfo.tmdb_title
        torinfo.cntitle = torinfo.tmdb_title

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

    def _score_result(self, result, preferred_titles, year):
        score = 0
        title = self._get_title(result)
        original_title = getattr(result, 'original_title', getattr(result, 'original_name', ''))
        resyear = self._get_year_from_datestr(getattr(result, 'release_date', '') or getattr(result, 'first_air_date', ''))

        # Year match bonus
        if year and resyear == year:
            score += 50
        
        # Title similarity
        if preferred_titles:
            for p in preferred_titles:
                if not p:
                    continue
                
                p_lower = p.strip().lower()
                title_lower = title.strip().lower()
                original_title_lower = original_title.strip().lower()

                # exact match
                if title_lower == p_lower or original_title_lower == p_lower:
                    score += 100
                
                # contains
                if p_lower in title_lower or p_lower in original_title_lower:
                    score += 30

                # LCS
                lcs_len = longest_common_subsequence_length(p, title)
                score += 2 * lcs_len

                # consecutive match
                cons_len, _, _ = find_longest_consecutive_match(p, title)
                score += 3 * cons_len
        
        # CJK title bonus
        if self.tmdb and getattr(self.tmdb, 'language', '') == 'zh-CN':
            if contains_cjk(title) or contains_cjk(original_title):
                score += 10
        
        # title length penalty (prefer shorter titles that are closer to search term length)
        if preferred_titles and preferred_titles[0]:
            score -= abs(len(title) - len(preferred_titles[0]))

        return score

    def _find_best_match(self, candidates, preferred_titles, year):
        if not candidates:
            return None
        
        best_result = None
        max_score = -float('inf')
        
        for res in candidates:
            score = self._score_result(res, preferred_titles, year)
            logger.trace(f"Scoring '{self._get_title(res)}' against '{preferred_titles}': {score}")
            if score > max_score:
                max_score = score
                best_result = res
        
        if best_result:
            logger.debug(f"Best match for '{preferred_titles}': '{self._get_title(best_result)}' with score {max_score}")
        
        return best_result

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
                # If movie search with year returns nothing, retry without year
                if not results and stryear:
                    logger.info(f'Retrying search for "{search_term}" in [movie] without year.')
                    results = search.movies(term=search_term, adult=True, year=None)
            else: # multi
                results = search.multi(term=search_term, adult=True, page=1) # year not supported in multi
        except Exception as e:
            logger.error(f"TMDb API search failed for '{search_term}': {e}")
            return None, None

        if not results:
            return None, None

        preferred_titles = [search_term]
        # Find best match with strict year check
        strict_candidates = self._find_year_match_list(results, year, strict=True)
        best_strict = self._find_best_match(strict_candidates, preferred_titles, year)
        if best_strict:
            return best_strict, 'strict'

        # If no strict match, find best match with fuzzy year check
        fuzzy_candidates = self._find_year_match_list(results, year, strict=False)
        best_fuzzy = self._find_best_match(fuzzy_candidates, preferred_titles, year)
        if best_fuzzy:
            return best_fuzzy, 'fuzzy'
            
        # No year match (or year was 0 or TV show)
        if not year or search_cat == 'tv':
             any_year_candidates = self._find_year_match_list(results, 0)
             best_any = self._find_best_match(any_year_candidates, preferred_titles, year)
             if best_any:
                return best_any, 'any'

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

        logger.debug(f"Search ==>  title: {title}, cntitle: {cntitle}, extitle: {extitle}, year:{intyear}, tmdb_cat:{torinfo.tmdb_cat}  init id_score: {torinfo.id_score}")

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
        title = re.sub(r'\s*[(（]\d{4}年?[)）]', '', title, flags=re.I) # 移除 (1957) 或 （1957年）
        title = re.sub(r'\[[^\]]*\]', '', title) # 移除方括号内容
        title = re.sub(r'^(Jade|\w{2,3}TV)\s+', '', title, flags=re.I)
        title = re.sub(r'\b(Extended|Anthology|Trilogy|Quadrilogy|Tetralogy|Collections?)\s*$', '', title, flags=re.I)
        # 移除各种质量/版本标识, 不再限制只在结尾
        title = re.sub(r'\b(HD|S\d+|E\d+|V\d+|4K|DVD|BluRay|WEB-DL|REMASTERED|CORRECTED|UnCut|SP)\b', '', title, flags=re.I)
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
            searches = [('tv', cuttitle), ('tv', cntitle), ('tv', extitle), ('multi', cuttitle), ('multi', cntitle)]
        elif torinfo.tmdb_cat == 'tv':
            torinfo.id_score += 5
            searches = [('tv', extitle), ('tv', cuttitle), ('tv', cntitle), ('multi', cntitle), ('multi', cuttitle)]
        elif torinfo.tmdb_cat == 'movie':
            searches = [('movie', extitle),  ('movie', cuttitle), ('movie', cntitle), ('multi', cuttitle), ('multi', cntitle)]
        else:
            searches = [('multi', extitle), ('multi', cntitle), ('multi', cuttitle), ('tv', cuttitle), ('movie', cuttitle)]

        # 过滤掉搜索关键字为空的条目，并移除重复的条目
        unique_list = list(dict.fromkeys(item for item in searches if item[1]))

        # 组合排序：
        # 1. 优先搜索包含中文的标题
        # 2. 如果cntitle太短，则优先使用cuttitle
        short_cntitle_case = len(cntitle) < 3 and len(cuttitle) > 5
        
        unique_list.sort(key=lambda item: (
            not contains_cjk(item[1]), 
            item[1] != cuttitle if short_cntitle_case else False
        ))
        
        return unique_list

    def _format_raw_results(self, results, media_type='multi'):
        processed_results = []
        # Handle both list and dict from tmdbv3api
        resultlist = results if isinstance(results, list) else results.get('results', [])
        for result in resultlist:
            media_cat = getattr(result, 'media_type', media_type)
            if media_cat not in ['movie', 'tv']:
                continue

            if media_cat == 'tv':
                title = getattr(result, 'name', getattr(result, 'original_name', ''))
                date_attr = 'first_air_date'
            else: # movie
                title = getattr(result, 'title', getattr(result, 'original_title', ''))
                date_attr = 'release_date'
            
            release_date = getattr(result, date_attr, '')
            year = self._get_year_from_datestr(release_date)

            processed_results.append(SimpleNamespace(
                id=result.id,
                title=title,
                original_title=getattr(result, 'original_title', getattr(result, 'original_name', '')),
                year=year,
                media_type=media_cat,
                poster_path=getattr(result, 'poster_path', ''),
                overview=getattr(result, 'overview', ''),
            ))
        return processed_results

    def search_tmdb_list(self, torinfo):
        title = torinfo.clean_title
        cntitle = torinfo.cntitle
        extitle = torinfo.extitle
        intyear = self._fix_year(torinfo)
        cuttitle = self._clean_title(title)

        logger.debug(f"Search List ==> title: {title}, cntitle: {cntitle}, extitle: {extitle}, year:{intyear}")

        search_list = self._build_search_list(torinfo, cntitle, cuttitle, extitle)
        logger.debug(f"search list: {search_list}")
        
        all_formatted_results = []
        processed_ids = set()
        search = Search()

        for category, term in search_list:
            if not term:
                continue
            
            try:
                if category == 'tv':
                    results = search.tv_shows(term=term, adult=True)
                elif category == 'movie':
                    results = search.movies(term=term, adult=True, year=str(intyear) if intyear else None)
                else: # multi
                    results = search.multi(term=term, adult=True, page=1)
            except Exception as e:
                logger.error(f"TMDb API search failed for '{term}': {e}")
                continue

            if not results:
                continue

            matched_results = self._find_year_match_list(results, intyear)

            if matched_results:
                # Format the results immediately, passing the correct category
                formatted_batch = self._format_raw_results(matched_results, media_type=category)
                for result_dict in formatted_batch:
                    if result_dict.id not in processed_ids:
                        all_formatted_results.append(result_dict)
                        processed_ids.add(result_dict.id)
        
        return all_formatted_results

    def search_tmdb_raw(self, search_term, media_type='multi', year=None):
        """
        Performs a raw search on TMDb and returns a list of results.
        """
        search = Search()
        results = []
        stryear = str(year) if year else None
        logger.info(f'Performing raw search for "{search_term}" in [{media_type}] with year: {stryear or "any"}')

        try:
            if media_type == 'tv':
                results = search.tv_shows(term=search_term, adult=True)
            elif media_type == 'movie':
                results = search.movies(term=search_term, adult=True, year=stryear)
            else: # multi
                results = search.multi(term=search_term, adult=True, page=1)
        except Exception as e:
            logger.error(f"TMDb API raw search failed for '{search_term}': {e}")
            return []
        
        intyear = self._fix_year(year) if year else 0 # Ensure year is int or 0
        matched_results = self._find_year_match_list(results, intyear)

        return self._format_raw_results(matched_results, media_type)

    def pick_best_raw_result(self, search_term, year=None, media_type='multi', preferred_titles=None):
        """
        Performs a raw TMDb search and returns the best-matching formatted result (dict).

        Selection strategy now uses the centralized `_find_best_match` method.
        `preferred_titles` should be a list of strings (e.g. [cntitle, clean_title, extitle]).
        """
        try:
            results = self.search_tmdb_raw(search_term, media_type=media_type, year=year)
        except Exception:
            return None

        if not results:
            return None

        # Normalize preferred_titles
        preferred = [p for p in (preferred_titles or []) if p]
        if not preferred and search_term:
            preferred = [search_term]


        # Quick pass: prefer exact title & year matches
        exact_matches = []
        if preferred:
            for p in preferred:
                if not p:
                    continue
                normalized_p = p.strip().lower()
                for r_obj in results:
                    r = vars(r_obj)
                    title_lower = (r.get('title') or '').strip().lower()
                    original_title_lower = (r.get('original_title') or '').strip().lower()
                    if title_lower == normalized_p or original_title_lower == normalized_p:
                        if not year or r.get('year') == year:
                            exact_matches.append(r_obj)

        if exact_matches:
            best_exact = self._find_best_match(exact_matches, preferred, year)
            if best_exact:
                return vars(best_exact)

        # Find the best match using the centralized scoring function
        best_result_obj = self._find_best_match(results, preferred, year)

        if best_result_obj:
            return vars(best_result_obj)

        # Fallback to first result if no good match is found
        return vars(results[0]) if results else None

    def populate_torinfo_from_raw(self, torinfo, raw_result):
        """
        Populate basic fields on a TorrentInfo object from a formatted raw TMDb result dict.
        Does not fetch full details; call `search_tmdb_by_tmdbid` afterwards to populate details.
        """
        if not raw_result:
            return torinfo

        torinfo.tmdb_id = str(raw_result.get('id'))
        torinfo.tmdb_cat = raw_result.get('media_type') or 'movie'
        torinfo.tmdb_title = raw_result.get('title') or raw_result.get('original_title')
        torinfo.poster_path = raw_result.get('poster_path')
        torinfo.overview = raw_result.get('overview')
        # Only overwrite year if we don't already have a valid one
        if not (isinstance(torinfo.year, int) and 1900 < torinfo.year < 2100):
            torinfo.year = raw_result.get('year') or torinfo.year

        return torinfo

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
            titlestr = re.sub(f'\b{roman}\b', arabic, titlestr, flags=re.IGNORECASE)
        return titlestr



    def _find_year_match_list(self, results, year, strict=False):
        matchList = []
        
        # Handle both list and dict from tmdbv3api
        resultlist = results if isinstance(results, list) else results.get('results', [])

        for result in resultlist:
            resyear = self._get_year_from_datestr(getattr(result, 'release_date', '') or getattr(result, 'first_air_date', ''))
            
            if year == 0: # If no year specified, all results are potential matches
                matchList.append(result)
                continue
            
            if strict:
                if resyear == year:
                    matchList.append(result)
            else: # fuzzy
                if resyear == 0: # If result has no year, it's a potential match
                    matchList.append(result)
                elif resyear in [year - 1, year, year + 1]: # Match within +/- 1 year
                    matchList.append(result)
        
        return matchList

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
        torinfo.imdb_id = getattr(details, 'imdb_id', None)
        torinfo.tmdb_backdrop = getattr(details, 'backdrop_path', '')
        if torinfo.tmdb_cat == 'movie':
            torinfo.tmdb_runtime = getattr(details, 'runtime', 0)
        elif torinfo.tmdb_cat == 'tv':
            if hasattr(details, 'episode_run_time') and details.episode_run_time:
                torinfo.tmdb_runtime = details.episode_run_time[0]
        
        torinfo.tmdb_popularity = getattr(details, 'popularity', 0)
        torinfo.tmdb_vote_average = getattr(details, 'vote_average', 0)
        torinfo.tmdb_vote_count = getattr(details, 'vote_count', 0)

        if hasattr(details, 'genres'):
            torinfo.tmdb_genres = ','.join([g.name for g in details.genres])

        if hasattr(details, 'casts') and hasattr(details.casts, 'cast'):
            cast_data = []
            for actor in itertools.islice(details.casts.cast, 20):
                cast_data.append({
                    'name': getattr(actor, 'name', ''),
                    'character': getattr(actor, 'character', ''),
                    'profile_path': getattr(actor, 'profile_path', ''),
                    'order': getattr(actor, 'order', 0)
                })
            torinfo.tmdb_casts = cast_data

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


