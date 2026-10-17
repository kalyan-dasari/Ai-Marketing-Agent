import sqlite3
import os
from flask import current_app, g

SCHEMA = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    website_url TEXT,
    repository_url TEXT,
    brief_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_sources (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_url TEXT,
    file_name TEXT,
    content TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    objective TEXT NOT NULL DEFAULT 'Get feedback',
    audience TEXT,
    platforms TEXT NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 7,
    tone TEXT NOT NULL DEFAULT 'Personal and useful',
    language TEXT NOT NULL DEFAULT 'English',
    cta TEXT,
    angles TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_assets (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    format TEXT NOT NULL,
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT,
    creative_brief TEXT,
    project_link TEXT,
    verification_notes TEXT,
    status TEXT NOT NULL DEFAULT 'needs_review' CHECK(status IN ('draft','needs_review','approved','rejected','queued','published','failed')),
    scheduled_for TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_versions (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE,
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE,
    platform TEXT,
    scheduled_for TEXT,
    published_at TEXT,
    external_id TEXT,
    external_url TEXT,
    error TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_metrics (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE,
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    video_views INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    notes TEXT,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    hypothesis TEXT,
    result_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS distribution_targets (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    target_name TEXT,
    url TEXT,
    rules_summary TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    shared_at TEXT,
    live_url TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assets_campaign ON content_assets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON content_assets(status);
CREATE INDEX IF NOT EXISTS idx_metrics_asset ON post_metrics(asset_id);
CREATE INDEX IF NOT EXISTS idx_dist_campaign ON distribution_targets(campaign_id);
'''

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def close_db(_=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def _run_migrations(db):
    """Safely apply schema migrations to existing database files."""
    def column_exists(table, column):
        cursor = db.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    # projects table migrations
    if not column_exists('projects', 'brief_json'):
        db.execute('ALTER TABLE projects ADD COLUMN brief_json TEXT')

    # project_sources migrations
    if not column_exists('project_sources', 'file_name'):
        db.execute('ALTER TABLE project_sources ADD COLUMN file_name TEXT')

    # campaigns migrations
    if not column_exists('campaigns', 'angles'):
        db.execute('ALTER TABLE campaigns ADD COLUMN angles TEXT')

    # scheduled_posts migrations
    if not column_exists('scheduled_posts', 'platform'):
        db.execute('ALTER TABLE scheduled_posts ADD COLUMN platform TEXT')
    if not column_exists('scheduled_posts', 'external_url'):
        db.execute('ALTER TABLE scheduled_posts ADD COLUMN external_url TEXT')
    if not column_exists('scheduled_posts', 'status'):
        db.execute('ALTER TABLE scheduled_posts ADD COLUMN status TEXT NOT NULL DEFAULT "scheduled"')

    # post_metrics migrations
    if not column_exists('post_metrics', 'conversions'):
        db.execute('ALTER TABLE post_metrics ADD COLUMN conversions INTEGER DEFAULT 0')
    if not column_exists('post_metrics', 'notes'):
        db.execute('ALTER TABLE post_metrics ADD COLUMN notes TEXT')

    # distribution_targets migrations
    if not column_exists('distribution_targets', 'created_at'):
        db.execute('ALTER TABLE distribution_targets ADD COLUMN created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP')

    # Ensure default settings exist
    default_settings = [
        ('ai_provider', 'mock'),
        ('ollama_url', 'http://127.0.0.1:11434'),
        ('ollama_model', 'llama3'),
        ('default_tone', 'Personal and useful')
    ]
    for key, val in default_settings:
        db.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))

    db.commit()

def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        _run_migrations(db)
        app.teardown_appcontext(close_db)

