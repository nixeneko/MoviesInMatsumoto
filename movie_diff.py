# coding: utf-8

import os, glob, json, copy, datetime

import getmovieinfo

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

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    latest_fn, before_fn = get_latest_jsonfilenames(2)
    latest_movies = load_json(latest_fn)
    before_movies = load_json(before_fn)
    
    for latest_movie in latest_movies:
        if latest_movie in before_movies:
            if not latest_movie.now_showing_flg: #上映予定のみ
                before_movie = list(filter(lambda x: latest_movie == x, before_movies))[0]
                if latest_movie.begin_date != before_movie.begin_date: #上映開始日に変更があった場合
                    print("Updated:", latest_movie)
        else:
            print("New:", latest_movie)
            
    for g in group_titles_together(filter_by_date(latest_movies, datetime.date(2021,4,2))):
        print("[", end="")
        for m in g:
            print(m.title, end=" ")
            print(m.theater, ", ", end="")
        print("]")
        
    #TODO:
    #a) 新しく追加された映画を通知
    #b) 次の日やその週の上映開始予定のものを通知
    #通知→テキストにする(文字数制限毎に分割してリストにする)
    # 上映予定日, タイトル, シアター
    # タイトルごとに、追加して文字数制限を超えるようなら次
    #投稿が被らない様にキャッシュする

if __name__ == "__main__":
    main()