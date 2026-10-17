from flask import Blueprint, render_template
from ..db import get_db
from ..services.analytics_service import AnalyticsService

web = Blueprint('web', __name__)

@web.get('/')
def index():
    db = get_db()
    projects = db.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    assets = db.execute('''
        SELECT a.*, c.name as campaign_name, p.name as project_name
        FROM content_assets a
        JOIN campaigns c ON c.id = a.campaign_id
        JOIN projects p ON p.id = c.project_id
        ORDER BY a.created_at DESC
    ''').fetchall()
    
    counts = {r['status']: r['n'] for r in db.execute('SELECT status, COUNT(*) as n FROM content_assets GROUP BY status').fetchall()}
    campaigns = db.execute('''
        SELECT c.*, p.name as project_name,
               (SELECT COUNT(*) FROM content_assets WHERE campaign_id = c.id) as total_assets,
               (SELECT COUNT(*) FROM content_assets WHERE campaign_id = c.id AND status = 'approved') as approved_assets
        FROM campaigns c
        JOIN projects p ON p.id = c.project_id
        ORDER BY c.created_at DESC
    ''').fetchall()

    settings_rows = db.execute('SELECT key, value FROM settings').fetchall()
    settings = {r['key']: r['value'] for r in settings_rows}

    targets = db.execute('''
        SELECT d.*, c.name as campaign_name, p.name as project_name
        FROM distribution_targets d
        JOIN campaigns c ON c.id = d.campaign_id
        JOIN projects p ON p.id = c.project_id
        ORDER BY d.created_at DESC LIMIT 10
    ''').fetchall()

    try:
        analytics = AnalyticsService.get_summary()
    except Exception:
        analytics = {'totals': {}, 'by_platform': {}, 'recommendations': []}

    return render_template(
        'index.html',
        projects=[dict(p) for p in projects],
        assets=[dict(a) for a in assets],
        counts=counts,
        campaigns=[dict(c) for c in campaigns],
        settings=settings,
        targets=[dict(t) for t in targets],
        analytics=analytics
    )
