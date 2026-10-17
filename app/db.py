import sqlite3
from flask import current_app, g

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, website_url TEXT, repository_url TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS project_sources (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, source_type TEXT NOT NULL, source_url TEXT, content TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, name TEXT NOT NULL, objective TEXT NOT NULL DEFAULT 'Get feedback', audience TEXT, platforms TEXT NOT NULL, duration_days INTEGER NOT NULL DEFAULT 7, tone TEXT NOT NULL DEFAULT 'Personal and useful', language TEXT NOT NULL DEFAULT 'English', cta TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS content_assets (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE, platform TEXT NOT NULL, format TEXT NOT NULL, hook TEXT NOT NULL, body TEXT NOT NULL, cta TEXT, creative_brief TEXT, project_link TEXT, verification_notes TEXT, status TEXT NOT NULL DEFAULT 'needs_review' CHECK(status IN ('draft','needs_review','approved','rejected','queued','published','failed')), scheduled_for TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS content_versions (id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE, hook TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS scheduled_posts (id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE, scheduled_for TEXT, published_at TEXT, external_id TEXT, error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS post_metrics (id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE, impressions INTEGER DEFAULT 0, reach INTEGER DEFAULT 0, engagements INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, video_views INTEGER DEFAULT 0, recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE, hypothesis TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS distribution_targets (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE, platform TEXT NOT NULL, target_name TEXT, url TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, entity_id INTEGER NOT NULL, action TEXT NOT NULL, details TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_assets_campaign ON content_assets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON content_assets(status);
'''

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def close_db(_=None):
    db = g.pop('db', None)
    if db is not None: db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()
        app.teardown_appcontext(close_db)
