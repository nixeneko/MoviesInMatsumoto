# coding: utf-8

#日本語
import mastodon_py_settings

import time
from mastodon import Mastodon
# Mastodon.py をインストールする
# pip install Mastodon.py
# https://github.com/halcy/Mastodon.py

APP_NAME = 'python_tooter' #アプリ名
MASTODON_URL = mastodon_py_settings.mastodon_server #MastodonサーバーのURL
CLIENT_CRED = 'python_tooter_clientcred.secret' #アプリの認証情報を保存するファイル
USER_CRED = mastodon_py_settings.access_token_file #ユーザーの認証情報を保存するファイル

LOGIN_MAIL_ADDRESS = 'login_mail_address@example.com'
LOGIN_PASSWORD = 'login_password'

# APPの登録
Mastodon.create_app(
     APP_NAME,
     api_base_url = MASTODON_URL,
     to_file = CLIENT_CRED
)

time.sleep(3)
# 認証情報の発行
mastodon = Mastodon(
    client_id = CLIENT_CRED,
    api_base_url = MASTODON_URL
)
mastodon.log_in(
    LOGIN_MAIL_ADDRESS,
    LOGIN_PASSWORD,
    to_file = USER_CRED
)
