import os
from typing import Optional
from flask import current_app
from .base import BaseAIProvider
from .mock import MockProvider
from .local_llm import LocalLLMProvider
from .groq_provider import GroqProvider
from ..db import get_db

def get_ai_provider() -> BaseAIProvider:
    """Returns configured AI provider based on settings or environment."""
    try:
        if current_app and current_app.config.get('TESTING'):
            return MockProvider()
    except Exception:
        pass

    try:
        db = get_db()
        rows = db.execute("SELECT key, value FROM settings WHERE key IN ('ai_provider', 'ollama_url', 'ollama_model', 'groq_api_key', 'groq_model')").fetchall()
        settings = {r['key']: r['value'] for r in rows}
    except Exception:
        settings = {}

    provider_type = settings.get('ai_provider')
    if not provider_type:
        provider_type = 'groq' if (settings.get('groq_api_key') or os.environ.get('GROQ_API_KEY')) else 'mock'

    if provider_type == 'groq':
        api_key = settings.get('groq_api_key') or os.environ.get('GROQ_API_KEY', '')
        model = settings.get('groq_model') or os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')
        return GroqProvider(api_key=api_key, model=model)

    if provider_type == 'local_llm':
        url = settings.get('ollama_url', 'http://127.0.0.1:11434')
        model = settings.get('ollama_model', 'llama3')
        return LocalLLMProvider(endpoint_url=url, model=model)
    
    return MockProvider()

