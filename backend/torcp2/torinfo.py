from dataclasses import dataclass
from typing import Optional
from tortitle import TorTitle, TorSubtitle

@dataclass
class TorrentInfo:
    # 基本信息
    torname: str = ''             # 种子文件名
    clean_title: str = ''         # 剥离出的 媒体标题
    cntitle: str = ''             # 剥离出的 中文标题信息
    season: Optional[str]  = ''   # 季度 (如 S01)
    episode: Optional[str] = ''   # 集 (如 E06)
    year: Optional[int] = 0       # 年份
    # infolink
    infolink: Optional[str] = ''  # 如果提供 
    subtitle: Optional[str] = ''  # 如果提供
    extitle: Optional[str] = ''   # 如果提供subtitle可解析出extitle

    # 技术参数
    resolution: Optional[str] = ''   # 分辨率 (1080p, 2160p等)
    media_source: Optional[str] = '' # 来源 (WEB-DL, BluRay等)
    video_codec: Optional[str] = ''  # 视频编码 (x264, x265等)
    audio_codec: Optional[str] = ''  # 音频编码 (AAC, AC3等)
    # 发布信息
    group: Optional[str] = ''       # 发布组名

    # 查询得到的
    tmdb_title: Optional[str] = ''          # 搜索得到的 媒体标题
    tmdb_cat: Optional[str] = ''          # 类型 (movie, tv)
    tmdb_id: Optional[str] = ''             # TMDb id
    imdb_id: Optional[str] = ''             # IMDb id
    imdb_val: Optional[float] = 0.0         # IMDb rate val  
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
   标题：{self.clean_title}
   季度：{self.season or 'N/A'}
   年份：{self.year or 'N/A'}

🛠 技术参数
   分辨率：{self.resolution or 'N/A'}
   片源：{self.media_source or 'N/A'}
   视频编码：{self.video_codec or 'N/A'}
   音频编码：{self.audio_codec or 'N/A'}

📋 发布信息
   发布组：{self.group or 'N/A'}
   副标题：{self.cntitle}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def tryint(instr):
    try:
        string_int = int(instr)
    except ValueError:    
        string_int = 0
    return string_int


class TorrentParser:
    """种子文件名解析器"""
    @classmethod
    def parse(cls, torname: str, subtitle: Optional[str] = None) -> Optional[TorrentInfo]:
        tt = TorTitle(torname)
        tst = None
        if subtitle:
            tst = TorSubtitle(subtitle)

        t = TorrentInfo()
        t.torname = torname
        t.clean_title = tt.title
        t.cntitle = tt.cntitle
        t.season = tt.season
        t.episode = tt.episode
        t.year = tryint(tt.year)
        if subtitle:
            t.subtitle = subtitle
            t.extitle = tst.extitle
        t.resolution = tt.resolution
        t.media_source = tt.media_source
        t.video_codec = tt.video
        t.audio_codec = tt.audio
        t.group = tt.group

        return t
    