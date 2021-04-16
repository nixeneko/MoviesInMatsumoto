# coding: utf-8

import os, glob, json, copy, datetime, time, sys
import pickle

import getmovieinfo
import post_mastodon

def get_latest_jsonfilenames(num=1):
    jsondir = getmovieinfo.JSON_DIR
    globtext = os.path.join(jsondir, "*.json")
    files = glob.glob(globtext)
    
    return list(reversed(sorted(files)))[0:num] #JSON_DIRに変な名前のJSONファイルがあるとこわれる

def load_json(filename):
    jsonstr = ""
    with open(filename, "r") as f:
        jsonstr = f.read()
    movies = json.loads(jsonstr, object_hook=getmovieinfo.as_movietitle)
    return movies
    
def filter_by_date(movielist, date_start, date_end=None):
    #date_start, date_end: datetime.date
    if date_start is None: return None
    if date_end is None:
        date_end = date_start
    return list(filter(lambda x: date_start <= x.begin_date <= date_end if x.begin_date else False, movielist))

def group_titles_together(movielist):
    copy_movielist = copy.copy(sorted(movielist))
    
    moviegroup_list = []
    while copy_movielist: # while not empty
        movie = copy_movielist.pop(0)
        moviegroup = [movie]
        same_titles = list(filter(lambda x: movie.is_same_title(x), copy_movielist))
        for title in same_titles:
            moviegroup.append(title)
            copy_movielist.remove(title)
        moviegroup_list.append(moviegroup)
    return moviegroup_list

#def group_by_date(movielist):

def diff_movies(before_movies, latest_movies):
    updated_movies = []
    new_movies = []
    for latest_movie in latest_movies:
        if latest_movie in before_movies:
            if not latest_movie.now_showing_flg: #上映予定のみ
                before_movie = list(filter(lambda x: latest_movie == x, before_movies))[0]
                if latest_movie.begin_date != before_movie.begin_date: #上映開始日に変更があった場合
                    updated_movies.append(latest_movie)
        else:
            new_movies.append(latest_movie)
    disappeared_movies = []
    for before_movie in before_movies:
        if before_movie not in latest_movies:
            disappeared_movies.append(before_movie)
    
    return updated_movies, new_movies, disappeared_movies

POSTED_PICKLE_FILE = "posted.pickle"
TEXT_MAX = 400
class MoviePoster():
    def _load_pickle(self):
        if os.path.isfile(POSTED_PICKLE_FILE):
            with open(POSTED_PICKLE_FILE, "rb") as f:
                return pickle.load(f)
        else: #ファイルが存在しない
            return [], {}
    def save_pickle(self):
        with open(POSTED_PICKLE_FILE, "wb") as w:
            pickle.dump([self.posted_movies, self.posted_times], w)
    def __init__(self):
        self.posted_movies, self.posted_times = self._load_pickle()
        # ここで過去のやつを削除
        
    def is_posted(self, movie):
        return movie in self.posted_movies
    def add_posted(self, movie):
        if movie not in self.posted_movies:
            self.posted_movies.append(movie)
    def post(self, s):
        post_mastodon.toot(s)
    def post_texts(self, ss):
        for s in ss:
            post_mastodon.toot(s)
            time.sleep(1)
    def post_movies(self, movies, text_header):
        texts = []
        text = ""
        for movie in movies:
            if self.is_posted(movie):
                print("ignored", movie)
                continue
            self.add_posted(movie)
            print("posting", movie)
            date_str = ""
            if movie.begin_date and movie.end_date:
                date_str = "{}({})～{}({})".format(
                    movie.begin_date.strftime("%m/%d"),
                    "月火水木金土日"[movie.begin_date.weekday()],
                    movie.end_date.strftime("%m/%d"),
                    "月火水木金土日"[movie.end_date.weekday()])
            elif movie.begin_date:
                date_str = "{}({})～".format(
                    movie.begin_date.strftime("%m/%d"),
                    "月火水木金土日"[movie.begin_date.weekday()])
            elif movie.when:
                date_str = movie.when
            else:
                continue
            movie_str = "{} {}: {}\n".format(
                date_str, movie.theater, movie.title)
            if len(text+movie_str) > TEXT_MAX-len(text_header):
                texts.append(text_header+text)
                text = ""
            text += movie_str
        if text:
            texts.append(text_header+text)
        self.post_texts(texts)
        self.save_pickle()
    def post_new_movies(self, movies):
        self.post_movies(movies, "上映予定が追加されました!\n")
    def post_updated_movies(self, movies):
        self.post_movies(movies, "上映日が決定しました!\n")
    #def post_movie_group(self, movie_groups):
    def is_posted_recently(self, when):
        if when in self.posted_times:
            if datetime.datetime.now() - self.posted_times[when] <= datetime.timedelta(hours=12):
                return True
        return False
    def add_posted_recently(self, when):
        self.posted_times[when] = datetime.datetime.now()
    def post_movies_to_show(self, movies, when=""):
        #TODO: whenとツイートした日付を記録し、12時間は同じ投稿をしないようにする
        if self.is_posted_recently(when):
            return
        text_header = when + "上映開始の映画です!\n"
        texts = []
        text = ""
        for group in group_titles_together(movies): #映画ごと
            title = ""
            theaters = []
            for movie in group:
                if not title:
                    title = movie.title
                theaters.append(movie.theater)
            movie_str = "{}: {}\n".format(title, ", ".join(theaters))
            if len(text + movie_str) > TEXT_MAX - len(text_header):
                texts.append(text_header + text)
                text = ""
            text += movie_str
        if text:
            texts.append(text_header + text)
        self.post_texts(texts)
        self.add_posted_recently(when)
        self.save_pickle()

def post_tomorrows_new(poster, latest_movies):
    print("明日の予定")
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_movies = filter_by_date(latest_movies, tomorrow)
    poster.post_movies_to_show(tomorrow_movies, "明日{}({})".format(
                    tomorrow.strftime("%m/%d"), "月火水木金土日"[tomorrow.weekday()]))

def post_todays_new(poster, latest_movies):
    print("今日の予定")
    today = datetime.date.today()
    today_movies = filter_by_date(latest_movies, today)
    poster.post_movies_to_show(today_movies, "今日{}({})".format(
                    today.strftime("%m/%d"), "月火水木金土日"[today.weekday()]))

def main(argv):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    latest_fn, before_fn = get_latest_jsonfilenames(2)
    #latest_fn, before_fn = "json/20210401-2254.json", "json/20210328-2158.json"
    latest_movies = load_json(latest_fn)
    before_movies = load_json(before_fn)
    
    updated_movies, new_movies, disappeared_movies = diff_movies(before_movies, latest_movies)

    poster = MoviePoster()
    print("新しい映画")
    poster.post_new_movies(new_movies)
    print("上映日決定")
    poster.post_updated_movies(updated_movies)
    print("消滅")
    for mov in disappeared_movies:
        print(mov)
    #ここから関数分けたいね
    if len(argv) == 1:
        post_tomorrows_new(poster, latest_movies)
    else:
        if argv[1] == "today":
            post_todays_new(poster, latest_movies)
        else:
            print("オプションが分かりません。")
    #TODO:
    #a) 新しく追加された映画を通知
    #b) 次の日やその週の上映開始予定のものを通知
    #通知→テキストにする(文字数制限毎に分割してリストにする)
    # 上映予定日, タイトル, シアター
    # タイトルごとに、追加して文字数制限を超えるようなら次
    #投稿が被らない様にキャッシュする

if __name__ == "__main__":
    main(sys.argv)