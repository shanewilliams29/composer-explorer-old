from flask import Blueprint

bp = Blueprint('composer', __name__)

from app.composer import routes
