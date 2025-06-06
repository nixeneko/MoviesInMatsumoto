# coding: utf-8

# Windowsコマンドライン対応
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                              encoding=sys.stdout.encoding, 
                              errors='backslashreplace', 
                              line_buffering=sys.stdout.line_buffering)

import urllib.request, urllib.parse
import os, re, datetime, json
import unicodedata
import bs4
import json5

# そのうちHTTPSになるかもしれない。そうしたら更新しないと…
THEATER_URL_DICT = {"アイシティシネマ": "https://www.inouedp.co.jp/icitycinema/",
                    "イオンシネマ松本": "https://www.aeoncinema.com/cinema/matsumoto/",
                    "シネマライツ": "http://cinema-lights8.com/",
                    "東座": "http://www.fromeastcinema.com/"}
#作品一覧データを取得するURL
URL_LIST = [
    ("http://cinema-lights8.com/", "lights.html"),
    ("https://www.inouedp.co.jp/icitycinema/timetable/", "icity_current.html"),
    ("https://www.inouedp.co.jp/icitycinema/schedule/", "icity_coming.html"),
    ("https://www.aeoncinema.com/cinema2/matsumoto/movie/index.html", "aeon_current.html"),
    ("https://www.aeoncinema.com/cinema2/matsumoto/movie/comingsoon.html", "aeon_coming.html"),
    ("https://www.aeoncinema.com/cinema2/matsumoto/movie/comingsoon2.html", "aeon_coming2.html"),
    ("http://www.fromeastcinema.com/data/azumaza-data.js", "azumaza-data.js"),
    ("http://www.fromeastcinema.com/data/azumaza-yokoku.js", "azumaza-yokoku.js"),
    ("http://www.fromeastcinema.com/data/fromeast-data.js", "fromeast-data.js"),
    ("http://www.fromeastcinema.com/data/fromeast-yokoku.js", "fromeast-yokoku.js")
    ]

DOWNLOADED_DIR = "downloaded" #取得したHTMLファイルを保存するディレクトリ
JSON_DIR = "json" #作品一覧データのJSONを出力するディレクトリ

TEMPLATE_HTML_FILE = "template.html"

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

FOLDER_TIME_FMT = "%Y%m%d-%H%M" #取得したHTMLを入れるサブフォルダの形式。strftimeに渡す
__recent_time_str = "" #キャッシュしちゃえ
def get_recently_downloaded():
    global __recent_time_str
    if __recent_time_str:
        return __recent_time_str
    timefmt = FOLDER_TIME_FMT
    now = datetime.datetime.now()
    now_str = now.strftime(timefmt)
    for d in os.listdir(path=DOWNLOADED_DIR):
        if os.path.isdir(os.path.join(DOWNLOADED_DIR, d)):
            m = re.match(r"\d{8}-\d{4}", d)
            if m:
                then = datetime.datetime.strptime(d, timefmt)
                if now - then < datetime.timedelta(hours=12): #12時間以内なら取得し直さない
                    __recent_time_str = d
                    return d
    return None

def download_htmls():
    time_str = get_recently_downloaded()
    if time_str is None:
        timefmt = FOLDER_TIME_FMT
        time_str = datetime.datetime.now().strftime(timefmt)
        dir = os.path.join(DOWNLOADED_DIR, time_str)
        os.makedirs(dir)
    dir = os.path.join(DOWNLOADED_DIR, time_str)
        
    for url, fnbase in URL_LIST:
        filename = os.path.join(dir, fnbase)
        if os.path.isfile(filename): #存在しなければダウンロード
            continue
        print("Downloading " + url)
        urllib.request.urlretrieve(url, filename)
    return time_str

def get_filepath_from_filename(filename):
    return os.path.join(DOWNLOADED_DIR, get_recently_downloaded(), filename)

def get_parsed_html_from_file(filename):
    html = None
    filepath = os.path.join(DOWNLOADED_DIR, get_recently_downloaded(), filename)
    with open(filepath, "r") as f:
        html = bs4.BeautifulSoup(f, "html.parser")
    return html

def tag2str(tag):
    text = ""
    if isinstance(tag, bs4.NavigableString):
        return str(tag).replace("\n", " ")
    if tag.name == "br":
        return "\n"
    for c in tag.children:
        text += tag2str(c)
    return text

def remove_multiple_space(s):
    return re.sub(r"\s+", " ", s)

def remove_space(s):
    return re.sub(r"\s+", "", s)

def remove_prefix(s): #先頭の"劇場版", "映画"等はソート時には無視(「映画」が先頭につく映画はこれで問題が起きる可能性はあるが…)
    # 残したい場合はリストに突っ込んで個別対応する
    EXCLUDE_LIST = ["映画大好きポンポさん"]
    for exclude_name in EXCLUDE_LIST:
        if s.startswith(exclude_name):
            return s
    return re.sub(r"^(劇場版|映画|劇場編集版|（旧作）|\(旧作\))", "", s).strip()
    
def remove_signs(s):
    return re.sub(r"""[「」『』"“”、。.．:：!！・/／ー－—−–\-～〜~]""", "", s)
    #音引き"ー"はあってもいいけど、入力ミスにより別の横棒になっている場合があり、消した方が安定する
def hira_to_kata(s): #http://python-remrin.hatenadiary.jp/entry/2017/04/26/123458
    return "".join([chr(ord(c) + 96) if ("ぁ" <= c <= "ゖ") else c for c in s])
    
def get_title_for_sorting(s):
    #Unicode正規化を通したほうが良い、全角英字などに対応するため
    txt = unicodedata.normalize('NFKC', s)
    #print(txt)
    return remove_space(hira_to_kata(remove_prefix(remove_signs(txt.lower()))))

class MovieTitle():
    def __init__(self, 
                title: str, 
                theater: str, 
                now_showing_flg: bool,
                when: str = "", 
                begin_date = None, # datetime.date or None
                end_date = None, # datetime.date or None
                url: str = ""
                ):
        self.title = remove_multiple_space(title).strip()
        self.title_for_sorting = get_title_for_sorting(self.title)
        self.theater = theater
        self.theater_url = THEATER_URL_DICT[theater]
        self.now_showing_flg = now_showing_flg
        self.when = when
        self.begin_date = begin_date
        self.end_date = end_date
        self.url = url
        #上映日より後なら上映中にする
        if self.now_showing_flg == False: #上映予定
            if self.begin_date and (self.begin_date <= datetime.date.today()):
                self.now_showing_flg = True
        
    def __str__(self):
        上映中か予定か = "上映中" if self.now_showing_flg else "上映予定"
        range_str = ""
        if self.begin_date or self.end_date:
            b_str = str(self.begin_date) if self.begin_date else ""
            e_str = str(self.end_date) if self.end_date else ""
            range_str = "{}～{}".format(b_str, e_str)
        return "{}: {}; {}; {}({}); {}".format(
                    上映中か予定か,
                    self.title,
                    self.theater,
                    self.when,
                    range_str,
                    self.url)
    def __lt__(self, other):
        if self.now_showing_flg == other.now_showing_flg:
            if self.now_showing_flg: #上映中
                if self.title_for_sorting == other.title_for_sorting:
                    return self.theater < other.theater
                else:
                    return self.title_for_sorting < other.title_for_sorting
            else: #上映予定
                if self.begin_date and other.begin_date:
                    if self.begin_date == other.begin_date:
                        if self.title_for_sorting == other.title_for_sorting:
                            return self.theater < other.theater
                        else:
                            return self.title_for_sorting < other.title_for_sorting
                    else:
                        return self.begin_date < other.begin_date
                elif self.begin_date: #other.begin_date == None
                    return True
                elif other.begin_date: #self.begin_date == None
                    return False
                else: #両方None
                    if self.title == other.title:
                        return self.theater < other.theater
                    else:
                        return self.title_for_sorting < other.title_for_sorting
        else:
            return self.now_showing_flg > other.now_showing_flg
    
    def __eq__(self, other): #タイトルが変化する場合もあり…そういう場合はどうしよう
        if type(self) != type(other): return False
        return self.title == other.title and self.theater == other.theater
    def __ne__(self, other):
        return not self.__eq__(other)
    def is_same_title(self, other):
        if type(self) != type(other): return False
        return self.title_for_sorting == other.title_for_sorting and self.begin_date == other.begin_date
    #公開日未定→決定なら通知したいけど公開日→公開中になったやつはそのままにしたい。
    #ひとまず開始日違いがあるのだけ判別しとるが…順序つけた方がいい気がする
    def is_updated(self, other): #日程が変更されてればTrue
        if self != ohter: return False #Falseでいいんかな?
        if self.begin_date and other.begin_date:
            return self.begin_date != other.begin_date
        if self.begin_date is None and other.begin_date:
            return True
        if self.begin_date and other.begin_date is None:
            return True
        return False
    
    def to_dict(self): #JSONableなやつを返す。冗長だけど。
        return {"title": self.title,
                "theater": self.theater,
                "theater_url": self.theater_url,
                "now_showing_flg": self.now_showing_flg,
                "when": self.when,
                "begin_date": self.begin_date.isoformat() if self.begin_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "url": self.url }
                
    @classmethod
    def from_dict(cls, dic):
        begin_date, end_date = None, None
        if dic["begin_date"]:
            begin_date = datetime.date.fromisoformat(dic["begin_date"])
        if dic["end_date"]:
            end_date = datetime.date.fromisoformat(dic["end_date"])
        return cls(
                dic["title"],
                dic["theater"],
                dic["now_showing_flg"],
                dic["when"],
                begin_date,
                end_date,
                dic["url"] )
                
    def to_tr_tag(self):
        tag_str = "<tr>"
        if self.now_showing_flg: #上映中…分ける必要ある?
            tag_str += '<td class="start_date">{}</td>'.format("上映中")
        else: #上映予定
            if self.begin_date:
                tag_str += '<td class="start_date">{}</td>'.format(
                                self.begin_date.strftime("%Y/%m/%d({})")
                                               .format("月火水木金土日"[self.begin_date.weekday()])
                                + ("" if self.begin_date == self.end_date else "～") #1日だけの上映の場合は"～"を入れない
                                )
            else:
                tag_str += '<td class="start_date">{}</td>'.format(self.when)
        if self.end_date:
            tag_str += '<td class="end_date">{}</td>'.format(
                                self.end_date.strftime("%Y/%m/%d"))
        else:
            tag_str += '<td class="end_date"></td>'
        if self.url:
            tag_str += '<td><a href="{}" target="_blank" rel="noopener noreferrer">{}</a></td>'.format(self.url, self.title)
        else:
            tag_str += '<td>{}</td>'.format(self.title)
        tag_str += '<td class="theater"><a href="{}" target="_blank" rel="noopener noreferrer">{}</a></td>'.format(self.theater_url, self.theater)
        tag_str += '<td class="when">{}</td>'.format(self.when)
        tag_str += "</tr>"
        return tag_str
             

def date_str2date(s): # 7/10(土)～ または ～4月2日（金） とか
    # 2021/4/1終了予定 とかにも対応
    if not s: return None
    date = None
    r_ymd = r"(\d{4})[/／年](\d{1,2})[/／月](\d{1,2})"
    m_ymd = re.search(r_ymd, s)
    if m_ymd:
        return datetime.date(int(m_ymd[1]), int(m_ymd[2]), int(m_ymd[3]))
    r = r"(\d{1,2}[/／月]\d{1,2})"
    m = re.search(r, s)
    if m:
        today = datetime.date.today()
        year = today.year
        
        month_str, day_str = m[1].replace("／", "/").replace("月", "/").split("/")
        month = int(month_str)
        day = int(day_str)
        date = datetime.date(year, month, day)
        if today - date > datetime.timedelta(days=90): #3か月以上前
            year+=1
            date = datetime.date(year, month, day)
    return date

def date_range_str2dates(s): # 7/10(土)～7/23(金) または 3月13日（土）～4月2日（金）
    #年は入力されないので適当に設定する
    #年を今年に設定した場合に開始日が今日の3か月以上前になるなら翌年とする
    #年が入っている表記を確認: 12月25日（土）～2022年1月14日
    #開始日が去年の場合がある
    #波ダッシュでなくハイフンであることがある
    if not s: return None, None
    begin_date = None
    end_date = None
    today = datetime.date.today()
    year = today.year
    # r = r"(\d{1,2}[/／月]\d{1,2})\D*[～〜~]\D*(\d{1,2}[/／月]\d{1,2})"
    r_begin = r"(\d{1,2}[/／月]\d{1,2})\D*[～〜~-]"
    m_begin = re.search(r_begin, s)
    if m_begin:
        # begin
        month_str, day_str = m_begin[1].replace("／", "/").replace("月", "/").split("/")
        month = int(month_str)
        day = int(day_str)
        begin_date = datetime.date(year, month, day)
        if today - begin_date > datetime.timedelta(days=90): #3か月以上前
            year+=1
            begin_date = datetime.date(year, month, day)
        elif begin_date - today > datetime.timedelta(days=300): #10カ月以上先
            year -= 1
            begin_date = datetime.date(year, month, day)
    r_end = r"[～〜~-]\D*((\d{2,4})[/／年])?(\d{1,2}[/／月]\d{1,2})"
    m_end = re.search(r_end, s)
    if m_end:
        # end
        # このコード、作ってみたけどゆーて要らん気がする
        # year_temp = m_end[2] #year
        # if year_temp: 
            # year_tmp_int = int(year_temp)
            # if year_tmp_int < 100: #2桁以内だったら西暦4桁にする
                # year = year_tmp_int + 2000
            # else:
                # year = year_tmp_int
                
        month_str, day_str = m_end[3].replace("／", "/").replace("月", "/").split("/")
        month = int(month_str)
        day = int(day_str)
        end_date = datetime.date(year, month, day)
        if begin_date is None:
            if today - end_date > datetime.timedelta(days=90): #3か月以上前
                end_date = datetime.date(year+1, month, day)
        elif end_date < begin_date: #開始時期よりも終了時期の方が早い
                end_date = datetime.date(year+1, month, day)
    return begin_date, end_date

def read_icitycinema_each_page(tabletag):
    theater = "アイシティシネマ"
    movie_list = []
    # table
    # td colspanが設定されない->映画とみる / 空なら無視
    # <a ...>～</a><br>の次の行～がタイトル
    # 次のspanが来るまでがタイトル?
    # <span style="color: #3366ff;">～</span>が公開予定時期
    tds = tabletag.find_all("td")
    
    上映中flg = True
    for td in tds:
        url = ""
        a = td.find("a")
        if a:
            url = a.get("href")
        #movie_text = td.get_text().strip()
        movie_text = tag2str(td).strip()
        
        if movie_text == "上映中作品":
            continue
        elif movie_text == "上映予定作品":
            上映中flg = False
            continue
        title_state = 0
        movie_title = ""
        when = ""
        lines = movie_text.split("\n")
        for i, line in enumerate(lines):
            l = line.strip()
            if i>=1:
                m = re.match(r"^(\d+/\d+|^\d+[年月])", l)
                n = re.match(r"([＜<](\d[DＤ])?/?(日本語)?(吹替|字幕)?(スーパー)?[＞>])+", l) # &lt;, &gt;は <, >に変換されてるっぽい
                if m:
                    title_state += 1
                    when += l
                elif       l.endswith("公開延期") \
                        or l.endswith("公開") \
                        or l.endswith("公開予定") \
                        or l.endswith("期間限定上映") \
                        or l.endswith("上映予定") \
                        or l.endswith("限定上映予定") \
                        or l.endswith("上映終了") \
                        or l.endswith("上映終了予定") \
                        or l.endswith("上映予定予定") \
                        or l.endswith("終了予定") \
                        or l.endswith("期間限定上映予定") \
                        or l.endswith("公開日未定"):
                    title_state += 1
                    when += l
                elif i>=1 and (l.startswith("©") or l.startswith("\u24d2") or l.startswith("\u24b8")):
                    title_state += 1
                elif l == "※PG12" or l == "※R15+" or l == "※R18+":
                    title_state += 1
                elif n: # <2D/字幕スーパー>など
                    title_state += 1
                else:
                    if title_state == 0:
                        if movie_title and l: 
                            movie_title += " "
                        movie_title += l
            else:
                if title_state == 0:
                    movie_title += l
        
        if movie_title:
            # もしmovie_titleが"※PG12" "※R15+" "※R18+"で終わるなら取り除く (このままだと全角半角で問題になる可能性あり)
            if movie_title.endswith("※PG12"):
                movie_title = movie_title.replace("※PG12", "").strip()
            elif movie_title.endswith("※R15+"):
                movie_title = movie_title.replace("※R15+", "").strip()
            elif movie_title.endswith("※R18+"):
                movie_title = movie_title.replace("※R18+", "").strip()
                
            begin_date, end_date = None, None
            if when:
                if when.endswith("公開") or when.endswith("公開予定"):
                    begin_date = date_str2date(when)
                elif when.endswith("期間限定上映") or when.endswith("期間限定上映予定") or when.endswith("限定上映予定"):
                    begin_date, end_date = date_range_str2dates(when)
                    if begin_date is None: #当然end_dateもNone
                        if 上映中flg: #上映中作品もこの表記で終了日が書かれることがある
                            end_date = date_str2date(when)
                        else:
                            begin_date = date_str2date(when)
                elif when.endswith("上映終了") or when.endswith("上映終了予定") or when.endswith("終了予定") \
                                                                            or when.endswith("上映予定予定"): #虹ヶ咲映画の表記ミスに対応"
                    end_date = date_str2date(when)
                else:
                    if not 上映中flg: #公開予定
                        begin_date = date_str2date(when)
            
            movie = MovieTitle(movie_title, theater, 上映中flg, 
                                when, begin_date, end_date, url)
            movie_list.append(movie)
    return movie_list
def read_icitycinema():
    #上映中
    html = get_parsed_html_from_file("icity_current.html")
    linkanchor = html.find(id="movieguide").parent
    for tag in linkanchor.next_siblings:
        if tag.name == "table":
            tabletag = tag
            break
    movie_list = read_icitycinema_each_page(tabletag)
    #上映予定
    coming_html = get_parsed_html_from_file("icity_coming.html")
    tabletag = coming_html.find("table")
    movie_list += read_icitycinema_each_page(tabletag)
    return movie_list

def read_cinemalights():
    fn = "lights.html"
    theater = "シネマライツ"
    movie_list = []
    html = get_parsed_html_from_file(fn)
    
    上映中count = 0 #「上映中」出現前には上映中とする
    
    tbl = html.find(class_="l_table")
    for tag in tbl.find_all(class_="movie_title"):
        _data = tag.find(class_="data")
        _data2 = tag.find(class_="data2")
        data = _data if _data else _data2
        if not data:    #空のとき
            continue
        data = data.get_text().strip()
        _p_title = tag.find(class_="title")
        _p_title2 = tag.find(class_="title2")
        p_title = _p_title if _p_title else _p_title2
        title = remove_multiple_space(p_title.get_text().strip())
        a_tag = p_title.find("a")
        url = a_tag.get("href") if a_tag else None
        
        #when = data if data != "上映中" else ""
        #上映中flg = bool(_data)
        if "上映中" in data: #"～上映中"に対応
            when = ""
            上映中flg = True
            上映中count += 1
        else:
            上映中flg = False
            when = data
            
        #終了予定が"～2/3"のようになっている場合に開始日としても取られてしまう問題が発生
        #dataとdata2で上映予定かどうかが区別できなくなったことにより発生
        #data/data2を区別せず、内容テキストにより判定することにする
        begin_date, end_date = date_range_str2dates(when) #whenが空ならNone, None
        if begin_date is None and end_date: #終了だけが指定されている場合、上映中とする
            上映中flg = True
        if when: #上映中flg==Falseになっている
            if "休映" in when: #"～休映" "平日休映～迄"
                begin_date, end_date = None, None
                上映中flg = True
            if begin_date is None and end_date is None: #幅で指定されてない場合
                some_kind_of_date = date_str2date(when)
                if some_kind_of_date: #何らかの日付が指定されていれば
                    if 上映中count > 0: #これから上映
                        begin_date = some_kind_of_date
                    else:
                        end_date = some_kind_of_date
        # when ~ "～\d{1,2}/\d{1,2}（.+）", "上映中", "\d{1,2}/\d{1,2}（.+）～?", "\d{2,4}年公開", "近日公開"
        
        if title:
            movie = MovieTitle(title, theater, 上映中flg, 
                                when, begin_date, end_date, url)
            movie_list.append(movie)
    return movie_list

def read_aeoncinema():
    fn = "aeon_current.html"
    base_url = [tpl[0] for tpl in URL_LIST if tpl[1] == fn][0]
    theater = "イオンシネマ松本"
    movie_list = []
    html = get_parsed_html_from_file(fn)
    #print(base_url)
    con_new_cinema = html.find(id="conNewCinema")
    for tag in con_new_cinema.find_all(class_="cinemaBlock"):
        cbTitle = tag.find(class_="cbTitle")
        title = cbTitle.get_text()
        rel_url = cbTitle.find("a").get("href")
        url = urllib.parse.urljoin(base_url, rel_url)
        when = ""
        end_date = None
        上映終了tag = tag.find(class_="cbb_jyoueisyuryo")
        if 上映終了tag:
            when = 上映終了tag.get_text().strip()
            end_date = date_str2date(when)
        上映中flg = True
        
        movie = MovieTitle(title, theater, 上映中flg, 
                            when=when, end_date=end_date, url=url) #URLは別ページ取得しないととれないので面倒ね
        movie_list.append(movie)
        
    fns = ["aeon_coming.html", "aeon_coming2.html"]
    for fn in fns:
        html = get_parsed_html_from_file(fn)
        
        con_new_cinema = html.find(id="conNewCinema")
        for tag in con_new_cinema.find_all(class_="cDateBlock"):
            start_when = tag.find(class_="startDate").get_text()
            上映中flg = False
            for tag2 in tag.find_all(class_="cinemaBlock"):
                cbTitle = tag2.find(class_="cbTitle")
                title = cbTitle.get_text()
                rel_url = cbTitle.find("a").get("href")
                url = urllib.parse.urljoin(base_url, rel_url)
                
                begin_date = None
                if start_when:
                    begin_date = date_str2date(start_when)
                
                end_when = ""
                end_date = None
                上映終了tag = tag2.find(class_="cbb_jyoueisyuryo")
                if 上映終了tag:
                    end_when = 上映終了tag.get_text().strip()
                    end_date = date_str2date(end_when)
                when = ""
                if end_when:
                    when = start_when + "～" + end_when.replace("終了予定", "")
                else:
                    when = start_when
                
                movie = MovieTitle(title, theater, 上映中flg, 
                                    when, begin_date, end_date, url=url)
                movie_list.append(movie)
    return movie_list

__today = datetime.date.today() #グローバルにしちゃえ
def is_now_showing(begin_date, end_date):
    if begin_date and end_date:
        return begin_date <= __today <= end_date
    elif begin_date:
        return begin_date <= __today
    elif end_date: #ここは適当
        return __today <= end_date
    else: #ほんとにこれでいい?想定されるのは上映中であるか、上映日時未定であるか。
        return False

def read_azumaza():
    theater = "東座"
    #movie_list = []
    movie_dict = {}
    showingfiles = ["azumaza-data.js", "fromeast-data.js"]
    yokokufiles = ["azumaza-yokoku.js", "fromeast-yokoku.js"]
    
    #上映中
    上映中flg = True
    for jsonfn in showingfiles:
        with open(get_filepath_from_filename(jsonfn), "r") as f:
            js_str = f.read()
        json_str = js_str[js_str.find("=")+1:js_str.find(";")].strip()
        json_loaded = json5.loads(json_str)
        
        for obj in json_loaded:
            title = obj["movie"]["title"] #
            url = obj["movie"]["siteUrl"] #
            when = obj["movie"]["date"] #"5月10日（土）～ 5月23日（金）",
            begin_date = datetime.date.fromisoformat(obj["movie"]["start"]) if obj["movie"]["start"] else None #"2025-05-10",
            end_date = datetime.date.fromisoformat(obj["movie"]["end"]) if obj["movie"]["end"] else None #"2025-05-23",

            # 「原題:」以降は消す
            title = re.sub(r"(原題|英題)[:：].+$", "", title)
            
            #begin_dateとend_dateがnullなことあるか？
            #if when:
            #    begin_date, end_date = date_range_str2dates(when)
            #    上映中flg = is_now_showing(begin_date, end_date)
            
            movie = MovieTitle(title, theater, 上映中flg, 
                                when, begin_date, end_date, url) #url信用できない
            #movie_list.append(movie)
            dict_key = begin_date.isoformat() + remove_multiple_space(title).split(" ")[0] #開始日とスペースの前の文字列だけで同一判定
            #begin_dateがNoneだとエラー出るなこれ
            movie_dict[dict_key] = movie
    #予告
    上映中flg = False
    for jsonfn in yokokufiles:
        with open(get_filepath_from_filename(jsonfn), "r") as f:
            js_str = f.read()
        json_str = js_str[js_str.find("=")+1:js_str.find(";")].strip()
        json_loaded = json5.loads(json_str)
        
        for obj in json_loaded: 
            title = obj["title"] 
            url = obj["link"] 
            when = obj["date"] #"5月10日（土）～ 5月23日（金）",
            begin_date = datetime.date.fromisoformat(obj["start"]) if obj["start"] else None #"2025-05-17"
            if begin_date is None:
                begin_date, end_date = date_range_str2dates(when)
            else:
                _, end_date = date_range_str2dates(when)
            上映中flg = is_now_showing(begin_date, end_date)

            # 「原題:」以降は消す
            title = re.sub(r"(原題|英題)[:：].+$", "", title)

            movie = MovieTitle(title, theater, 上映中flg, 
                                when, begin_date, end_date, url) #url信用できない
            if begin_date:
                dict_key = begin_date.isoformat() + remove_multiple_space(title).split(" ")[0] #開始日とスペースの前の文字列だけで同一判定
            else:
                dict_key = remove_multiple_space(title).split(" ")[0] #開始日が不明ならスペースの前の文字列だけで同一判定
            overlap_flg = False
            for key in movie_dict.keys():
                if dict_key.startswith(key) or key.startswith(dict_key):
                    if len(dict_key) > 13 and len(key) > 13: #一応文字数が少なすぎるとアレかなあというのでつけてみている 10文字は日付
                        overlap_flg = True
            if not overlap_flg:
                movie_dict[dict_key] = movie

    return movie_dict.values()
    
class MovieEncoder(json.JSONEncoder): #for json.dump
    def default(self, obj): 
        if isinstance(obj, MovieTitle):
            return obj.to_dict()
        return json.JSONEncoder.default(self, obj)
def as_movietitle(dct): #for json.load
    if "title" in dct and "theater" in dct:
        return MovieTitle.from_dict(dct)
    return json.JSONDecoder.decode(self, dct)
    
def make_html_tag(movie_list, time_str):
    tag_str = ""
    with open(TEMPLATE_HTML_FILE, "r") as f:
        tag_str = f.read()
    
    date_updated = time_str[0:4]+"/"+time_str[4:6]+"/"+time_str[6:8]
    table_data = ""
    for movie in movie_list:
        table_data += movie.to_tr_tag() + "\n"
    return tag_str.format(  date_updated=date_updated,
                            table_data=table_data,
                            url_icity=THEATER_URL_DICT["アイシティシネマ"],
                            url_aeon=THEATER_URL_DICT["イオンシネマ松本"],
                            url_lights=THEATER_URL_DICT["シネマライツ"],
                            url_azumaza=THEATER_URL_DICT["東座"])

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    time_str = download_htmls()
    global __today
    __today = datetime.date(int(time_str[0:4]), int(time_str[4:6]), int(time_str[6:8]))
    movies = []
    movies += read_icitycinema()
    movies += read_cinemalights()
    movies += read_aeoncinema()
    movies += read_azumaza()
    # アドホック
    # begin_date, end_date = datetime.date(2021, 4, 16), datetime.date(2021, 4, 22)
    # 上映中flg = begin_date <= __today
    # if end_date >= __today:
        # movies.append(MovieTitle("るろうに剣心 伝説の最期編", "アイシティシネマ", 上映中flg, "4/16（金）～4/22（木）", begin_date, end_date))
    
    #movies = json.loads(jsonstr, object_hook=as_movietitle)
    movies = sorted(movies)
    json_path = os.path.join(JSON_DIR, time_str+".json")
    #if not os.path.isfile(json_path):
    with open(json_path, "w") as w:
        json.dump(movies, w, ensure_ascii=False, indent=2, cls=MovieEncoder)
    html_str = make_html_tag(movies, time_str)
    with open("docs/index.html", "w") as w:
        w.write(html_str)
    
if __name__ == "__main__":
    main()