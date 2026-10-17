import json, logging
from flask import Blueprint, jsonify, request
from ..db import get_db
from ..providers.mock import MockProvider
api=Blueprint('api',__name__)
log=logging.getLogger(__name__)
STATUSES={'draft','needs_review','approved','rejected','queued','published','failed'}

def error(message, code=400): return jsonify({'error':message}), code

@api.get('/projects')
def projects():
    rows=get_db().execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])

@api.post('/projects')
def create_project():
    data=request.get_json(silent=True) or {}
    name=(data.get('name') or '').strip(); desc=(data.get('description') or '').strip()
    if not name or not desc: return error('Project name and description are required.')
    if len(name)>120 or len(desc)>5000: return error('Name must be 120 characters or fewer and description 5,000 or fewer.')
    db=get_db(); cur=db.execute('INSERT INTO projects(name,description,website_url,repository_url) VALUES(?,?,?,?)',(name,desc,data.get('website_url'),data.get('repository_url'))); db.commit()
    return jsonify(dict(db.execute('SELECT * FROM projects WHERE id=?',(cur.lastrowid,)).fetchone())),201

@api.get('/campaigns')
def campaigns():
    return jsonify([dict(r) for r in get_db().execute('SELECT c.*,p.name project_name FROM campaigns c JOIN projects p ON p.id=c.project_id ORDER BY c.created_at DESC')])

@api.post('/campaigns')
def create_campaign():
    data=request.get_json(silent=True) or {}; db=get_db()
    project=db.execute('SELECT * FROM projects WHERE id=?',(data.get('project_id'),)).fetchone()
    if not project: return error('Choose an existing project.')
    platforms=data.get('platforms') or ['LinkedIn','Instagram','Reddit']
    allowed={'LinkedIn','Instagram','Reddit'}
    if not isinstance(platforms,list) or not platforms or any(p not in allowed for p in platforms): return error('Platforms must be selected from LinkedIn, Instagram, and Reddit.')
    cur=db.execute('INSERT INTO campaigns(project_id,name,objective,audience,platforms,duration_days,tone,language,cta) VALUES(?,?,?,?,?,?,?,?,?)',(project['id'],(data.get('name') or f"{project['name']} campaign")[:160],data.get('objective','Get feedback')[:200],data.get('audience','')[:500],json.dumps(platforms),max(1,min(int(data.get('duration_days',7)),90)),data.get('tone','Personal and useful')[:100],data.get('language','English')[:50],data.get('cta','')[:300]))
    campaign=db.execute('SELECT * FROM campaigns WHERE id=?',(cur.lastrowid,)).fetchone()
    drafts=MockProvider().generate_campaign(dict(project),dict(campaign))
    for i,item in enumerate(drafts):
        if item['platform'] not in platforms: continue
        db.execute('INSERT INTO content_assets(campaign_id,platform,format,hook,body,cta,creative_brief,project_link,verification_notes,status,scheduled_for) VALUES(?,?,?,?,?,?,?,?,?,?,datetime(\'now\',?))',(cur.lastrowid,item['platform'],item['format'],item['hook'],item['body'],item['cta'],item['creative_brief'],project['website_url'] or project['repository_url'],item['verification_notes'],'needs_review',f'+{i} days'))
    db.execute('INSERT INTO audit_events(entity_type,entity_id,action,details) VALUES(?,?,?,?)',('campaign',cur.lastrowid,'generated','Deterministic mock provider'))
    db.commit()
    return jsonify({'campaign':dict(campaign),'assets':[dict(r) for r in db.execute('SELECT * FROM content_assets WHERE campaign_id=? ORDER BY id',(cur.lastrowid,))]}),201

@api.get('/assets')
def assets():
    rows=get_db().execute('SELECT a.*,c.name campaign_name,p.name project_name FROM content_assets a JOIN campaigns c ON c.id=a.campaign_id JOIN projects p ON p.id=c.project_id ORDER BY a.created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])

@api.patch('/assets/<int:asset_id>')
def edit_asset(asset_id):
    data=request.get_json(silent=True) or {}; db=get_db(); asset=db.execute('SELECT * FROM content_assets WHERE id=?',(asset_id,)).fetchone()
    if not asset:return error('Asset not found.',404)
    hook=data.get('hook',asset['hook']); body=data.get('body',asset['body'])
    if not isinstance(hook,str) or not hook.strip() or not isinstance(body,str) or not body.strip():return error('Hook and content cannot be empty.')
    changed=hook!=asset['hook'] or body!=asset['body']
    if changed:
        db.execute('INSERT INTO content_versions(asset_id,hook,body) VALUES(?,?,?)',(asset_id,asset['hook'],asset['body']))
    status='needs_review' if changed and asset['status']=='approved' else asset['status']
    db.execute('UPDATE content_assets SET hook=?,body=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(hook.strip()[:500],body.strip()[:10000],status,asset_id))
    db.execute('INSERT INTO audit_events(entity_type,entity_id,action,details) VALUES(?,?,?,?)',('asset',asset_id,'edited',f'status={status}'))
    db.commit(); return jsonify(dict(db.execute('SELECT * FROM content_assets WHERE id=?',(asset_id,)).fetchone()))

@api.post('/assets/<int:asset_id>/status')
def set_status(asset_id):
    data=request.get_json(silent=True) or {}; status=data.get('status')
    if status not in STATUSES:return error('Invalid content status.')
    db=get_db(); asset=db.execute('SELECT status FROM content_assets WHERE id=?',(asset_id,)).fetchone()
    if not asset:return error('Asset not found.',404)
    if status in {'approved','queued','published'} and asset['status'] not in {'needs_review','approved','queued'}:return error('Only reviewed content can be approved or published.')
    if status in {'queued','published'} and asset['status']!='approved':return error('Approve this content before scheduling or publishing.')
    db.execute('UPDATE content_assets SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,asset_id))
    db.execute('INSERT INTO audit_events(entity_type,entity_id,action,details) VALUES(?,?,?,?)',('asset',asset_id,'status_changed',status)); db.commit()
    return jsonify(dict(db.execute('SELECT * FROM content_assets WHERE id=?',(asset_id,)).fetchone()))
