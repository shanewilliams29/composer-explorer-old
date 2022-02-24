import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    MAX_CONTENT_LENGTH = 1024 * 1024 * 5

    SECRET_KEY = os.environ.get('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMINS = ['composerexplorer@gmail.com']
    ADMIN_NAME = 'AGBL816N1JNRIG'

    POSTS_PER_PAGE = 50

    SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URL = os.environ.get('SPOTIFY_REDIRECT_URL')

    BING_SEARCH_KEY = os.environ.get('BING_SEARCH_KEY')

    STATIC = 'https://storage.googleapis.com/composer-explorer.appspot.com/'

    SITE_NAME = "ComposerExplorer Forum"
    SITE_DESCRIPTION = "Welcome to the ComposerExplorer forums. A place to discuss classical music composers, works and recordings."
