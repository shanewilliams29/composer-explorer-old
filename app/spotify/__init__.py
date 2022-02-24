from flask import Blueprint
from app import Config
from app.spotify.classes import SpotifyAPI

bp = Blueprint('spotify', __name__)

sp = SpotifyAPI(Config.SPOTIFY_CLIENT_ID, Config.SPOTIFY_CLIENT_SECRET, Config.SPOTIFY_REDIRECT_URL)

from app.spotify import routes
