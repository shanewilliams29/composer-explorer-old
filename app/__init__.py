from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_mobility import Mobility
from google.cloud import logging
from flask_caching import Cache
import time

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
mobility = Mobility()
log = logging.Client()
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    mobility.init_app(app)
    cache.init_app(app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.user import bp as user_bp
    app.register_blueprint(user_bp)

    from app.spotify import bp as spotify_bp
    app.register_blueprint(spotify_bp)

    from app.composer import bp as composer_bp
    app.register_blueprint(composer_bp)

    from app.albums import bp as albums_bp
    app.register_blueprint(albums_bp)

    from app.forum import bp as forum_bp
    app.register_blueprint(forum_bp)

    from app.composeralbums import bp as composeralbums_bp
    app.register_blueprint(composeralbums_bp)

    from app.cron import bp as cron_bp
    app.register_blueprint(cron_bp)

    # Debugging

    # if not app.debug and not app.testing:
    #     if app.config['MAIL_SERVER']:
    #         auth = None
    #         if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
    #             auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    #         secure = None
    #         if app.config['MAIL_USE_TLS']:
    #             secure = ()
    #         mail_handler = SMTPHandler(
    #             mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
    #             fromaddr='no-reply@' + app.config['MAIL_SERVER'],
    #             toaddrs=app.config['ADMINS'], subject='Compexplorer Failure',
    #             credentials=auth, secure=secure)
    #         mail_handler.setLevel(logging.ERROR)
    #         app.logger.addHandler(mail_handler)

    return app


from app import models
