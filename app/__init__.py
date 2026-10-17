import logging
from flask import Flask
from .config import Config
from .db import init_db
from .routes.web import web
from .routes.api import api

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)
    init_db(app)
    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix='/api/v1')
    return app
