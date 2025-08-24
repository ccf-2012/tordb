import re
import os


def cut_ext(tor_name):
    if not tor_name:
        return ''
    tortup = os.path.splitext(tor_name)
    torext = tortup[1].lower()
    # if re.match(r'\.[0-9a-z]{2,5}$', tortup[1], flags=re.I):
    mvext = ['.mkv', '.ts', '.m2ts', '.vob', '.mpg', '.mp4', '.3gp', '.mov', '.tp', '.zip', '.pdf', '.iso', '.ass', '.srt', '.7z', '.rar']
    if torext.lower() in mvext:
        return tortup[0].strip()
    else:
        return tor_name

def delimer_to_space(sstr):
    dilimers = ['[', ']', '.', '{', '}', '_', ',', '(', ')' ]
    for dchar in dilimers:
        sstr = sstr.replace(dchar, ' ')
    return sstr

def hyphen_to_space(sstr):
    return sstr.replace('-', ' ')

def cutspan(sstr, ifrom, ito):
    if (ifrom >= 0) and (len(sstr) > ito):
        sstr = sstr[0:ifrom:] + sstr[ito::]
    return sstr

def contains_cjk(str):
    return re.search(r'[\u4e00-\u9fa5\u3041-\u30fc]', str)

def cut_aka(titlestr):
    m = re.search(r'\s(/|AKA)\s', titlestr, re.I)
    if m:
        titlestr = titlestr.split(m.group(0))[0]
    return titlestr.strip()

def tryint(str):
    cndigit = '一二三四五六七八九十'
    if str[0] in cndigit and len(str) == 1:
        return cndigit.index(str[0]) + 1
    try:
        return int(str)
    except:
        return 0

def is_0day_name(itemstr):
    # CoComelon.S03.1080p.NF.WEB-DL.DDP2.0.H.264-NPMS
    m = re.match(r'^\w+.*\b(BluRay|Blu-?ray|720p|1080[pi]|[xh].?26\d|2160p|576i|WEB-DL|DVD|WEBRip|HDTV)\b.*', itemstr, flags=re.A | re.I)
    return m

class TorTitle:
    def __init__(self, name):
        self.raw_name = name
        self.title = name
        self.cntitle = ''
        self.year = ''
        self.type = 'movie'
        self.season = ''
        self.episode = ''
        self.sub_episode = ''
        # self.season_int = None
        # self.episode_int = None
        self._se_pos = 0
        self._year_pos = 0
        self.parse()

    def parse(self):
        self._handle_bracket_title()
        parsing_target = self.raw_name
        if self.title != self.raw_name:
            parsing_target = self.title
        self._prepare_title()
        self._extract_year()
        self._extract_type()
        self._extract_titles()
        self._polish_title()
        # self._handle_special_cases()
        self.media_source, self.video, self.audio = self._parse_more(self.raw_name)
        self.group = self._parse_group(parsing_target)
        self.resolution = self._parse_resolution(self.raw_name)
        self.full_season = (self.type == 'tv') and (self.episode == '')


    def _parse_more(self, torName):
        mediaSource, video, audio = '', '', ''
        if m := re.search(r"(?<=(1080p|2160p)\s)(((\w+)\s+)?WEB(-DL)?)|\bWEB(-DL)?\b|\bHDTV\b|((UHD )?(BluRay|Blu-ray))", torName, re.I):
            m0 = m[0].strip()
            if re.search(r'WEB[-]?(DL)?', m0, re.I):
                mediaSource = 'webdl'
            elif re.search(r'BLURAY|BLU-RAY', m0, re.I):
                if re.search(r'x26[45]', torName, re.I):
                    mediaSource = 'encode'
                elif re.search(r'remux', torName, re.I):
                    mediaSource = 'remux'
                else:
                    mediaSource = 'bluray'
            else:
                mediaSource = m0
        if m := re.search(r"AVC|HEVC(\s(DV|HDR))?|H\.?26[456](\s(HDR|DV))?|x26[45]\s?(10bit)?(HDR)?|DoVi (HDR(10)?)? (HEVC)?", torName, re.I):
            video = m[0].strip()
        if m := re.search(r"DTS-HD MA \d.\d|LPCM\s?\d.\d|TrueHD\s?\d\.\d( Atmos)?|DDP[\s\.]*\d\.\d( Atmos)?|(AAC|FLAC)(\s*\d\.\d)?( Atmos)?|DTS(\s?\d\.\d)?|DD\+? \d\.\d", torName, re.I):
            audio = m[0].strip()
        return mediaSource, video, audio

    def _parse_resolution(self, torName):
        match = re.search(r'\b(4K|2160p|1080[pi]|720p|576p|480p)\b', torName, re.A | re.I)
        if match:
            r = match.group(0).strip().lower()
            if r == '4k':
                r = '2160p'
            return r
        else:
            return ''
        
    def _parse_group(self, torName):
        sstr = cut_ext(torName)
        match = re.search(r'[@\-￡]\s?(\w+)(?!.*[@\-￡].*)$', sstr, re.I)
        if match:
            groupName = match.group(1).strip()
            # # TODO: BD-50_A_PORTRAIT_OF_SHUNKIN_1976_BC
            if match.span(1)[0] < 4:
                return None
            if groupName.startswith('CMCT') and not groupName.startswith('CMCTV'):
                groupName = 'CMCT'
            return groupName

        return None
        
    def _prepare_title(self):
        self.title = cut_ext(self.title)
        self.title = re.sub(r'^【.*】', '', self.title, flags=re.I)
        self.title = re.sub(r'^\w+TV\b', '', self.title, flags=re.I)
        self.title = delimer_to_space(self.title)

    def _handle_bracket_title(self):
        if self.title.startswith('[') and self.title.endswith(']'):
            parts = [part.strip() for part in self.title[1:-1].split('][') if part.strip()]
            keyword_pattern = r'1080p|2160p|720p|H\.?26[45]|x26[45]'
            
            main_part = ''
            cjk_parts = []

            keyword_idx = -1
            for idx, part in enumerate(parts):
                if re.search(keyword_pattern, part, re.I):
                    keyword_idx = idx
                    main_part = part
            
            if main_part:
                if re.match(r'^'+keyword_pattern+'$', main_part, flags=re.I):
                    if keyword_idx > 0:
                        self.title = parts[keyword_idx-1]
                        keyword_idx = keyword_idx - 1
                else:
                    self.title = main_part
                if keyword_idx > 0 and contains_cjk(parts[keyword_idx-1]):
                    full_cntitle = parts[keyword_idx-1]
                    full_cntitle = re.sub(r'大陆|港台', '', full_cntitle, flags=re.I)
                    self.cntitle = full_cntitle.split(' ')[0].strip()


    def _extract_year(self):
        potential_years = re.findall(r'(19\d{2}|20\d{2})(?:\d{4})?\b', self.title)
        if potential_years:
            self.year = potential_years[-1]
            self._year_pos = self.title.rfind(self.year)
            # if self.title.strip() != self.year:
            #     self.title = self.title.replace(self.year, ' ')

    def _extract_type(self):
        patterns = {
            's_e': r'\b(S\d+)(E\d+(-Ep?\d+)?)\b',
            'season_only': r'(?<![a-zA-Z])(S\d+([\-\+]S?\d+)?)\b(?!.*\bS\d+)',
            'season_word': r'\bSeason (\d+)\b',
            'ep_only': r'\bEp?(\d+)(-Ep?\d+)?\b',
            'cn_season': r'第([一二三四五六七八九十]|\d+)季',
            'cn_episode': r'第([一二三四五六七八九十]+|\d+)集'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, self.title, flags=re.IGNORECASE)
            if match:
                self.type = 'tv'
                if key in ['s_e']:
                    # self.season_int = int(match.group(1))
                    # self.episode_int = int(match.group(2))
                    self.season = match.group(1)
                    self.episode = match.group(2)
                elif key == 'season_only':
                    # self.season_int = tryint(match.group(1))
                    self.season = match.group(0)
                elif key in ['season_word', 'cn_season']:
                    # self.season_int = tryint(match.group(1))
                    season_int = tryint(match.group(1))
                    self.season = 'S'+ str(season_int).zfill(2) if season_int else ''
                elif key in ['cn_episode', 'ep_only']:
                    self.season = 'S01'
                    self.episode = match.group()

                self._se_pos = match.span(0)[0]
                return

    def _cut_s_year_season(self):
        positions = [p for p in [self._year_pos, self._se_pos] if p > 0]
        if positions:
            cut_pos = min(positions)
            self.title = self.title[:cut_pos]
        self.title = self.title.strip()

    def _cut_s_keyword(self):
        tags = [
            '2160p', '1080p', '720p', '480p', 'BluRay', r'(4K)?\s*Remux', 
            r'WEB-?(DL)?', r'(?<![a-z])4K', r'(?<=\w\s)BDMV',
        ]
        pattern = r'(' + '|'.join(tag for tag in tags) + r')\b.*$'
        self.title = re.sub(pattern, '', self.title, flags=re.IGNORECASE)
        self.title = self.title.strip()
    
    def _extract_titles(self):
        failsafe = self.title
        self._cut_s_year_season()
        failsafe = self.title if len(self.title) > 0 else failsafe
        self._cut_s_keyword()

        if not self.cntitle:
            if contains_cjk(self.title):
                self.cntitle = self.title
                if m := re.search(r"([一-鿆]+[\-0-9a-zA-Z]*)[ :：]+([^一-鿆]+\b)", self.title, flags=re.I):
                    self.cntitle = self.cntitle[:m.span(1)[1]]
                    self.title = m.group(2)

                # 删去：汉字之前，有空格分隔的 ascii 字符串
                if m1 := re.match(r'^([^一-鿆]*)[\s\(\[]+[一-鿆]', self.cntitle, flags=re.I):
                    self.cntitle = self.cntitle.replace(m1.group(1), '').strip()

                # 取汉字串中第一个空格前部分
                if self.cntitle:
                    match = re.match(r'^([^ \-\(\[]*)', self.cntitle)
                    if match:
                        self.cntitle = match.group()

        self.title = self.title.strip()
        if not self.title:
            self.title = failsafe
        return

    def _check_title(self):
        m1 = re.search('[a-zA-Z]', self.title)
        if len(self.title) > 2 and m1:
            return True
        else:
            return False

    def _polish_title(self):
        self.title = re.sub(r'[\._\+]', ' ', self.title)
        tags = [
            'BTV', r'CCTV\s*\d+(HD|\+)?', 'HunanTV', r'Top\s*\d+',
            r'\b\w+版', r'全\d+集', 'BDMV',
            'COMPLETE', 'REPACK', 'PROPER', r'REMASTER\w*',
            'iNTERNAL', 'LIMITED', 'EXTENDED', 'UNRATED', 
            "Director's Cut"
        ]
        pattern = r'\b(' + '|'.join(tag for tag in tags) + r')\b'
        self.title = re.sub(pattern, '', self.title, flags=re.IGNORECASE)
        self.title = self.title.strip()

        self.title = hyphen_to_space(self.title)
        self.title = cut_aka(self.title)

        if not self._check_title() and self.cntitle:
            self.title = self.cntitle

        # self.title = re.sub(r'\s+', ' ', self.title).strip()
        # self.title = self.title.split('-')[0].strip()

    def _handle_special_cases(self):
        pass

    def to_dict(self):
        return {
            'title': self.title,
            'cntitle': self.cntitle,
            'year': self.year,
            'type': self.type,
            'season': self.season,
            'episode': self.episode
        }

def parse_tor_name(name):
    return TorTitle(name)
