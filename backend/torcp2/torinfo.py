from dataclasses import dataclass
from typing import Optional
import os, re, sys
import tortitle
import torcategory

@dataclass
class TorrentInfo:
    # 基本信息
    torname: str = ''             # 种子文件名
    media_title: str = ''         # 剥离出的 媒体标题
    tmdb_title: str = ''          # 搜索得到的 媒体标题
    season: Optional[str]  = ''    # 季度 (如 S01)
    episode: Optional[str] = ''   # 集 (如 E06)
    year: Optional[int] = 0      # 年份
    # infolink
    infolink: str = ''
    subtitle: str = ''
    # 技术参数
    resolution: Optional[str] = ''   # 分辨率 (1080p, 2160p等)
    source: Optional[str] = ''      # 来源 (WEB-DL, BluRay等)
    video_codec: Optional[str] = ''  # 视频编码 (x264, x265等)
    audio_codec: Optional[str] = ''  # 音频编码 (AAC, AC3等)
    # 发布信息
    group: Optional[str] = ''       # 发布组名
    subtitle: str = ''              # 副标题信息

    # 查询得到的
    tmdb_cat: str = ''          # 类型 (movie, tv)
    tmdb_id: str = ''             # TMDb id
    imdb_id: str = ''             # IMDb id
    imdb_val: float = 0.0         # IMDb rate val  
    original_language: Optional[str] = ''   # 语言
    popularity: Optional[float] = 0      # 
    poster_path: Optional[str] = ''        # 
    release_air_date: Optional[str] = ''     # 

    genre_ids =[]
    tmdbDetails = None
    origin_country = ''
    original_title = ''
    overview = ''
    vote_average = 0
    production_countries = ''
    confidence = 0

    def __str__(self) -> str:
        """美化输出格式"""
        return f"""
📦 种子信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 基本信息
   类型：{self.tmdb_cat}
   标题：{self.media_title}
   季度：{self.season or 'N/A'}
   年份：{self.year or 'N/A'}

🛠 技术参数
   分辨率：{self.resolution or 'N/A'}
   片源：{self.source or 'N/A'}
   视频编码：{self.video_codec or 'N/A'}
   音频编码：{self.audio_codec or 'N/A'}

📋 发布信息
   发布组：{self.group or 'N/A'}
   副标题：{self.subtitle}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def tryint(instr):
    try:
        string_int = int(instr)
    except ValueError:    
        string_int = 0
    return string_int


def transFromCCFCat(cat):
    if re.match(r'(Movie)', cat, re.I):
        return 'movie'
    elif re.match(r'(TV)', cat, re.I):
        return 'tv'
    else:
        return cat


class TorrentParser:
    """种子文件名解析器"""
    @classmethod
    def parse(cls, torname: str) -> Optional[TorrentInfo]:
        tc = torcategory.TorCategory(torname)
        tt = tortitle.TorTitle(torname)
        title, parseYear, season, episode, cntitle = tt.title, tt.year, tt.season, tt.episode, tt.cntitle 
        mediaSource, videoCodec, audioCodec = tt.parse_more(torname)
        year = tryint(parseYear)

        t= TorrentInfo()
        t.tmdb_cat=transFromCCFCat(tc.ccfcat)
        t.media_title=cntitle if cntitle else title
        t.tmdb_title = ''
        t.torname=torname
        t.season=season
        t.episode=episode
        t.year=year
        t.resolution=tc.resolution
        t.source=mediaSource
        t.video_codec=videoCodec
        t.audio_codec=audioCodec
        t.group=tc.group
        t.subtitle=cntitle
        return t
    