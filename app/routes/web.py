from flask import Blueprint, render_template
from ..db import get_db
web = Blueprint('web', __name__)
@web.get('/')
def index():
    db=get_db()
    projects=db.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    assets=db.execute('SELECT a.*,c.name campaign_name,p.name project_name FROM content_assets a JOIN campaigns c ON c.id=a.campaign_id JOIN projects p ON p.id=c.project_id ORDER BY a.created_at DESC LIMIT 8').fetchall()
    counts={r['status']:r['n'] for r in db.execute('SELECT status,COUNT(*) n FROM content_assets GROUP BY status').fetchall()}
    campaigns=db.execute('SELECT c.*,p.name project_name FROM campaigns c JOIN projects p ON p.id=c.project_id ORDER BY c.created_at DESC LIMIT 5').fetchall()
    return render_template('index.html',projects=projects,assets=assets,counts=counts,campaigns=campaigns)
