import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'local-development-only-change-before-deploy')
    DATABASE = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'project_to_reach.sqlite3'))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
