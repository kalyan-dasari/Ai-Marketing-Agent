import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'local-development-only-change-before-deploy')
    DATABASE = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'project_to_reach.sqlite3'))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')
