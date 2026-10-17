from typing import Optional
from flask import current_app
from .base import BaseAIProvider
from .mock import MockProvider
from .local_llm import LocalLLMProvider
from ..db import get_db

def get_ai_provider() -> BaseAIProvider:
    """Returns configured AI provider based on settings."""
    try:
        db = get_db()
        rows = db.execute("SELECT key, value FROM settings WHERE key IN ('ai_provider', 'ollama_url', 'ollama_model')").fetchall()
        settings = {r['key']: r['value'] for r in rows}
    except Exception:
        settings = {}

    provider_type = settings.get('ai_provider', 'mock')
    if provider_type == 'local_llm':
        url = settings.get('ollama_url', 'http://127.0.0.1:11434')
        model = settings.get('ollama_model', 'llama3')
        return LocalLLMProvider(endpoint_url=url, model=model)
    
    return MockProvider()
