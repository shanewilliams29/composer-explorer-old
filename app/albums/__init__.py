from flask import Blueprint

bp = Blueprint('albums', __name__)

from app.albums import routes
