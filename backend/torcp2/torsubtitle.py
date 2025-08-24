"""
This module provides a class to parse movie and series information from raw subtitle names.
"""
import re

# Dictionary to map Chinese numerals to integers
CHINESE_NUMERALS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
}

def chinese_to_arabic(s: str) -> int | None:
    """Converts a Chinese numeral string to an integer."""
    return CHINESE_NUMERALS.get(s)

def contains_cjk(str):
    return re.search(r'[\u4e00-\u9fa5\u3041-\u30fc]', str)

class TorSubtitle:
    """
    Parses a raw subtitle string to extract title, season, and episode information.
    """
    def __init__(self, raw_name: str):
        """
        Initializes the TorSubtitle object and parses the raw name.

        Args:
            raw_name: The raw string from the subtitle file name or torrent title.
        """
        self.raw_name = raw_name
        self.extitle = ""
        self.season = ""
        self.episode = ""
        self.total_episodes = ""

        self._parse()

    def _parse_season(self, name: str):
        """Parses season information."""
        # Pattern for "第三季", "Season 4"
        season_pattern = r'(?:第([一二三四五六七八九十]+|[0-9]+)季|Season\s*([0-9]+))'
        match = re.search(season_pattern, name, re.IGNORECASE)
        if match:
            season_str = match.group(1) or match.group(2)
            if season_str.isdigit():
                self.season = int(season_str)
            else:
                self.season = chinese_to_arabic(season_str)

    def _parse_episode(self, name: str):
        """Parses episode information."""
        # Pattern for "第01集", "第1-2集", "第1-10集", "全10集"
        episode_pattern = r'(?:第([0-9]+(?:-[0-9]+)?)集|全([0-9]+)集)'
        match = re.search(episode_pattern, name)
        if match:
            episode_str = ""
            if match.group(1):  # "第1-2集" or "第1集"
                episode_str = match.group(1)
            elif match.group(2):  # "全10集"
                self.total_episodes = int(match.group(2))
                # episode_str = f"1-{self.total_episodes}"

            if '-' in episode_str:
                parts = episode_str.split('-')
                start = parts[0].zfill(2)
                end = parts[1].zfill(2)
                self.episode = f"E{start}-E{end}"
            elif episode_str:
                self.episode = f"E{episode_str.zfill(2)}"


    def _parse_extitle(self, name: str):
        """Parses the main title (extitle)."""
        self.extitle = ""
        processed_name = name.strip()
        # [] 【 】都展开，对中文标题来说，标以这样方括号的，有可能是主要信息
        processed_name = re.sub(r"\[|\]|【|】", " ", processed_name).strip()
        # 这些开头的，直接不处理
        if m := re.match(r"^(0day破解|第.{1,4}[季|集]|[简中].*?字幕|主演|无损)\b", processed_name, flags=re.I):
            self.extitle = ''
            return

        # 开头的一些可能字词，先删掉：...新番，官方国语中字，国漫，国家，xxx剧，xxx台/卫视，综艺，带上分隔符一起删
        processed_name = re.sub(r"\d+\s*年\s*\d+\s*月\s*\w*番[\:：\s/\|]?", "", processed_name)
        # 开头的官方国语中字 跟:：
        processed_name = re.sub(r"^\w*(官方|禁转|国语|中字|国漫|特效)[\:：\s/\|]", "", processed_name).strip()
        # 开头是国家、XYZTV、卫视，带上分隔符一起删
        processed_name = re.sub(r"^(日本|瑞典|挪威|大陆|香港|港台|\w剧|(墨西哥|新加坡)剧|\w国)[\:：\s/\|]", "", processed_name)
        processed_name = re.sub(r"^(\w+TV|Jade|TVB\w*|HOYTV|点播|翡翠台|\w*卫视|电影|韩综)\b", "", processed_name)
        # 墨西哥剧：，英剧，美国...后跟 ：:|，带上分隔符一起删
        processed_name = re.sub(r"\b(连载\w*|\w*国漫)[\:：\s\|]", "", processed_name)

        # 干扰字词，可能在开头，或前2格
        processed_name = re.sub(r"\b([全第]\w{,4}\s*集|第\d+集|S\d+|(\d+-\d+集)|第.{1,4}[季|集]|纪录|专辑|综艺|动画|剧场版)\b", "", processed_name)
        processed_name = re.sub(r"1080p|2160p|720p|4K\b|IMax\b|杜比视界|中\w双语", "", processed_name)

        processed_name = processed_name.strip()

        # \|\s分隔的各个part，含有以下字词则抛弃
        main_parts = re.split(r'[丨|/ \s]', processed_name)
        ignore_patterns = re.compile(r"\b官方|国语|国配|中字|特效|DIY|国漫|\b\w国\b|点播\b|\w+字幕|简繁|翡翠台|\w*卫视|中\w+频道|PTP Gold.*?corn|\w+TV\b|类别[:：]|\b无损\b|原盘\b", re.IGNORECASE)

        for part in main_parts:
            candidate = re.sub(r'\(|\)|（|）', ' ', part).strip()
            # 有中字的部分，且，包含上述字词
            if not contains_cjk(part):
                continue
            if ignore_patterns.match(candidate):
                continue

            # If it starts with Chinese, we can split by space to separate title and version/other info
            if re.match(r'[\u4e00-\u9fa5]', candidate):
                candidate = candidate.split(' ')[0]

            candidate = candidate.strip()
            if candidate and not ignore_patterns.match(candidate):
                self.extitle = candidate
                return

        return 
        # Fallback: if all parts are filtered, return the first part if it exists, else empty string
        # self.extitle = main_parts[0].strip() if main_parts else ""


    def _parse(self):
        """
        Runs the parsing logic for season, episode, and title.
        """
        self._parse_season(self.raw_name)
        self._parse_episode(self.raw_name)
        self._parse_extitle(self.raw_name)

    def to_dict(self):
        """Returns the parsed data as a dictionary."""
        return {
            "raw_name": self.raw_name,
            "extitle": self.extitle,
            "season": self.season,
            "episode": self.episode,
            "total_episodes": self.total_episodes,
        }

# For backward compatibility, we can keep a function that uses the class.
def parse_subtitle(name: str) -> str:
    """
    Parses a raw subtitle string to extract the movie/series title.
    This is a wrapper for the TorSubtitle class for backward compatibility.
    """
    return TorSubtitle(name).extitle
