from flask import Blueprint

bp = Blueprint('composeralbums', __name__)

from app.composeralbums import routes
