# MoviesInMatsumoto
長野県・松本地区で上映している映画の一覧を取得して表示するページを作ります。

映画一覧を次のページで公開しています: https://nixeneko.github.io/MoviesInMatsumoto/  
また、過去の映画一覧のJSONファイルを json フォルダに納めています。

## モチベーション
よく行く映画館での上映予定の映画が一覧できなかったので作りました。
見たかったけど近くでやってなかった映画が来週から一週間限定公開！ということがあったので…

## 方針
- Webページの更新(というか、push)は手動でやります。何らかの事情があって更新できなくなったらごめんなさい。
- 各映画館のWebページのHTMLを取得して解析します。
- 映画の画像は使いません。これは主に権利上の問題です。
- 映画の同一判定はなるべくせず、人間が見て判別できればいいと割り切っています。
- 上映予定は各映画館のWebサイトの表現をほぼそのまま使っているので統一がとれていません。
- 映画のURLは壊れている可能性があります。

### 並び順
- ソートはMovieTitleクラスの__lt__で定義しています。Pythonで並べ替え、Webページでは並べ替えはしません。
- ①上映中, ②上映予定のもので上映日が決まっているものは日付順, ③上映予定で上映日未定の順に並べています。
- 上映日が同じものについてはタイトルでUnicode順に並びます。ただし…
  - ソート時には、タイトル先頭の“劇場版”, “映画”は無視します。また、スペース、一部の記号類も無視します。
    - タイトルが“映画”で始まる映画は壊れる可能性があるので、そういうものが出てきたら考えます。
  - ひらがなとカタカナは同一視します。


