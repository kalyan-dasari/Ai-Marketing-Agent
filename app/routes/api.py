import json
import logging
from flask import Blueprint, jsonify, request
from ..services.project_service import ProjectService
from ..services.campaign_service import CampaignService
from ..services.distribution_service import DistributionService
from ..services.analytics_service import AnalyticsService
from ..providers.local_llm import LocalLLMProvider
from ..db import get_db

api = Blueprint('api', __name__)
log = logging.getLogger(__name__)

def error_response(message: str, code: int = 400):
    return jsonify({'error': str(message)}), code

# ==================== PROJECTS ====================

@api.get('/projects')
def get_projects():
    try:
        return jsonify(ProjectService.get_all_projects())
    except Exception as e:
        log.error(f"Error fetching projects: {e}")
        return error_response(e, 500)

@api.post('/projects')
def create_project():
    data = request.get_json(silent=True) or {}
    try:
        project = ProjectService.create_project(
            name=data.get('name'),
            description=data.get('description'),
            website_url=data.get('website_url'),
            repository_url=data.get('repository_url')
        )
        return jsonify(project), 201
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        log.error(f"Error creating project: {e}")
        return error_response("An unexpected error occurred creating the project.", 500)

@api.get('/projects/<int:project_id>')
def get_project(project_id: int):
    project = ProjectService.get_project_by_id(project_id)
    if not project:
        return error_response("Project not found.", 404)
    return jsonify(project)

@api.post('/projects/<int:project_id>/sources/upload')
def upload_project_source(project_id: int):
    # Support both multipart form file and json text payload
    if 'file' in request.files:
        uploaded_file = request.files['file']
        if not uploaded_file.filename:
            return error_response("No file selected.")
        try:
            content = uploaded_file.read().decode('utf-8', errors='replace')
            result = ProjectService.add_uploaded_file(project_id, uploaded_file.filename, content)
            return jsonify(result), 201
        except ValueError as e:
            return error_response(e, 400)
        except Exception as e:
            return error_response(f"Upload failed: {str(e)}", 500)

    data = request.get_json(silent=True) or {}
    filename = data.get('filename') or 'uploaded_document.md'
    content = data.get('content') or ''
    try:
        result = ProjectService.add_uploaded_file(project_id, filename, content)
        return jsonify(result), 201
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"Upload failed: {str(e)}", 500)

@api.post('/projects/<int:project_id>/sources/fetch-github')
def fetch_github_source(project_id: int):
    data = request.get_json(silent=True) or {}
    github_url = data.get('github_url')
    if not github_url:
        return error_response("github_url is required.")
    try:
        result = ProjectService.fetch_github_readme(project_id, github_url)
        return jsonify(result), 201
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"GitHub fetch failed: {str(e)}", 500)

@api.post('/projects/<int:project_id>/analyze')
def analyze_project(project_id: int):
    try:
        brief = ProjectService.generate_project_brief(project_id)
        return jsonify(brief), 200
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"Analysis failed: {str(e)}", 500)

# ==================== CAMPAIGNS ====================

@api.get('/campaigns')
def get_campaigns():
    try:
        return jsonify(CampaignService.get_all_campaigns())
    except Exception as e:
        return error_response(e, 500)

@api.post('/campaigns')
def create_campaign():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    if not project_id:
        return error_response("project_id is required.")

    try:
        campaign = CampaignService.create_campaign(
            project_id=int(project_id),
            name=data.get('name'),
            objective=data.get('objective', 'Get feedback'),
            audience=data.get('audience', ''),
            platforms=data.get('platforms'),
            duration_days=int(data.get('duration_days', 7)),
            tone=data.get('tone', 'Personal and useful'),
            language=data.get('language', 'English'),
            cta=data.get('cta', ''),
            angles=data.get('angles')
        )
        return jsonify(campaign), 201
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        log.error(f"Error creating campaign: {e}")
        return error_response(f"Failed to generate campaign: {str(e)}", 500)

@api.get('/campaigns/<int:campaign_id>')
def get_campaign(campaign_id: int):
    c = CampaignService.get_campaign_by_id(campaign_id)
    if not c:
        return error_response("Campaign not found.", 404)
    return jsonify(c)

# ==================== CONTENT ASSETS & STUDIO ====================

@api.get('/assets')
def get_assets():
    filters = {}
    if request.args.get('campaign_id'):
        filters['campaign_id'] = int(request.args.get('campaign_id'))
    if request.args.get('platform'):
        filters['platform'] = request.args.get('platform')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    try:
        return jsonify(CampaignService.get_assets(filters))
    except Exception as e:
        return error_response(e, 500)

@api.patch('/assets/<int:asset_id>')
def edit_asset(asset_id: int):
    data = request.get_json(silent=True) or {}
    try:
        updated = CampaignService.edit_asset(
            asset_id=asset_id,
            hook=data.get('hook', ''),
            body=data.get('body', ''),
            cta=data.get('cta'),
            creative_brief=data.get('creative_brief'),
            scheduled_for=data.get('scheduled_for')
        )
        return jsonify(updated)
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"Failed to edit asset: {str(e)}", 500)

@api.post('/assets/<int:asset_id>/status')
def set_asset_status(asset_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if not status:
        return error_response("status is required.")
    try:
        updated = CampaignService.set_asset_status(asset_id, status)
        return jsonify(updated)
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"Failed to update status: {str(e)}", 500)

@api.post('/assets/<int:asset_id>/regenerate')
def regenerate_asset(asset_id: int):
    data = request.get_json(silent=True) or {}
    instruction = (data.get('instruction') or '').strip()
    try:
        updated = CampaignService.regenerate_asset(asset_id, instruction)
        return jsonify(updated)
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(f"Regeneration failed: {str(e)}", 500)

@api.get('/assets/<int:asset_id>/versions')
def get_asset_versions(asset_id: int):
    try:
        return jsonify(CampaignService.get_asset_versions(asset_id))
    except Exception as e:
        return error_response(e, 500)

# ==================== CALENDAR ====================

@api.get('/calendar/events')
def get_calendar_events():
    db = get_db()
    rows = db.execute("""
        SELECT a.id, a.platform, a.format, a.hook, a.status, a.scheduled_for,
               c.name as campaign_name, p.name as project_name
        FROM content_assets a
        JOIN campaigns c ON c.id = a.campaign_id
        JOIN projects p ON p.id = c.project_id
        WHERE a.scheduled_for IS NOT NULL
        ORDER BY a.scheduled_for ASC
    """).fetchall()
    return jsonify([dict(r) for r in rows])

# ==================== DISTRIBUTION TRACKER ====================

@api.get('/distribution/targets')
def get_distribution_targets():
    campaign_id = request.args.get('campaign_id', type=int)
    return jsonify(DistributionService.get_targets(campaign_id))

@api.post('/distribution/targets')
def add_distribution_target():
    data = request.get_json(silent=True) or {}
    try:
        target = DistributionService.add_target(
            campaign_id=int(data.get('campaign_id')),
            platform=data.get('platform', 'Reddit'),
            target_name=data.get('target_name', ''),
            url=data.get('url', ''),
            rules_summary=data.get('rules_summary', '')
        )
        return jsonify(target), 201
    except Exception as e:
        return error_response(e, 400)

@api.post('/distribution/targets/<int:target_id>/shared')
def mark_target_shared(target_id: int):
    data = request.get_json(silent=True) or {}
    try:
        result = DistributionService.mark_shared(
            target_id=target_id,
            live_url=data.get('live_url', ''),
            notes=data.get('notes', '')
        )
        return jsonify(result)
    except Exception as e:
        return error_response(e, 400)

# ==================== ANALYTICS ====================

@api.get('/analytics/summary')
def get_analytics_summary():
    try:
        return jsonify(AnalyticsService.get_summary())
    except Exception as e:
        return error_response(e, 500)

@api.post('/analytics/metrics')
def record_metrics():
    data = request.get_json(silent=True) or {}
    asset_id = data.get('asset_id')
    if not asset_id:
        return error_response("asset_id is required.")
    try:
        result = AnalyticsService.record_metrics(
            asset_id=int(asset_id),
            impressions=int(data.get('impressions', 0)),
            reach=int(data.get('reach', 0)),
            engagements=int(data.get('engagements', 0)),
            clicks=int(data.get('clicks', 0)),
            video_views=int(data.get('video_views', 0)),
            conversions=int(data.get('conversions', 0)),
            notes=data.get('notes', '')
        )
        return jsonify(result), 201
    except ValueError as e:
        return error_response(e, 400)
    except Exception as e:
        return error_response(e, 500)

# ==================== SETTINGS & PROVIDERS ====================

@api.get('/settings')
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return jsonify({r['key']: r['value'] for r in rows})

@api.post('/settings')
def update_settings():
    data = request.get_json(silent=True) or {}
    db = get_db()
    for key in ['ai_provider', 'ollama_url', 'ollama_model', 'default_tone']:
        if key in data:
            db.execute("INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (key, str(data[key]).strip()))
    db.commit()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return jsonify({r['key']: r['value'] for r in rows})

@api.post('/settings/test-local-llm')
def test_local_llm():
    data = request.get_json(silent=True) or {}
    url = data.get('ollama_url') or 'http://127.0.0.1:11434'
    model = data.get('ollama_model') or 'llama3'
    provider = LocalLLMProvider(endpoint_url=url, model=model)
    success, message = provider.test_connection()
    return jsonify({'success': success, 'message': message}), (200 if success else 400)

@api.get('/audit')
def get_audit_logs():
    db = get_db()
    rows = db.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 50").fetchall()
    return jsonify([dict(r) for r in rows])
