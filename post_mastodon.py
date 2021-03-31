# coding: utf-8

#日本語
import mastodon_py_settings

from mastodon import Mastodon
# Mastodon.py
mastodon = Mastodon(
    access_token = mastodon_py_settings.access_token_file,
    api_base_url = mastodon_py_settings.mastodon_server
)

def toot(s):
    mastodon.toot(s)

