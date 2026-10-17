import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..db import get_db
from ..providers.factory import get_ai_provider

log = logging.getLogger(__name__)

STATUSES = {'draft', 'needs_review', 'approved', 'rejected', 'queued', 'published', 'failed'}

class CampaignService:
    @staticmethod
    def get_all_campaigns() -> List[Dict[str, Any]]:
        db = get_db()
        rows = db.execute("""
            SELECT c.*, p.name as project_name,
                   (SELECT COUNT(*) FROM content_assets WHERE campaign_id = c.id) as total_assets,
                   (SELECT COUNT(*) FROM content_assets WHERE campaign_id = c.id AND status = 'approved') as approved_assets,
                   (SELECT COUNT(*) FROM content_assets WHERE campaign_id = c.id AND status = 'needs_review') as pending_assets
            FROM campaigns c
            JOIN projects p ON p.id = c.project_id
            ORDER BY c.created_at DESC
        """).fetchall()
        result = []
        for r in rows:
            c = dict(r)
            if isinstance(c.get('platforms'), str):
                try:
                    c['platforms'] = json.loads(c['platforms'])
                except Exception:
                    pass
            result.append(c)
        return result

    @staticmethod
    def get_campaign_by_id(campaign_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = db.execute("""
            SELECT c.*, p.name as project_name, p.website_url, p.repository_url
            FROM campaigns c
            JOIN projects p ON p.id = c.project_id
            WHERE c.id = ?
        """, (campaign_id,)).fetchone()
        if not row:
            return None
        c = dict(row)
        if isinstance(c.get('platforms'), str):
            try:
                c['platforms'] = json.loads(c['platforms'])
            except Exception:
                pass
        
        # Load assets
        assets = db.execute("SELECT * FROM content_assets WHERE campaign_id = ? ORDER BY scheduled_for ASC, id ASC", (campaign_id,)).fetchall()
        c['assets'] = [dict(a) for a in assets]
        return c

    @staticmethod
    def create_campaign(
        project_id: int,
        name: Optional[str] = None,
        objective: str = 'Get feedback',
        audience: str = '',
        platforms: Optional[List[str]] = None,
        duration_days: int = 7,
        tone: str = 'Personal and useful',
        language: str = 'English',
        cta: str = '',
        angles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        db = get_db()
        project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError("Selected project does not exist.")

        allowed_platforms = {'LinkedIn', 'Instagram', 'Reddit'}
        if not platforms:
            platforms = ['LinkedIn', 'Instagram', 'Reddit']
        if not isinstance(platforms, list) or any(p not in allowed_platforms for p in platforms):
            raise ValueError("Platforms must be chosen from LinkedIn, Instagram, and Reddit.")

        duration_days = max(1, min(int(duration_days), 90))
        campaign_name = (name or f"{project['name']} campaign").strip()[:160]

        # Parse project brief if available
        brief = None
        if project['brief_json']:
            try:
                brief = json.loads(project['brief_json'])
            except Exception:
                pass

        cur = db.execute("""
            INSERT INTO campaigns (project_id, name, objective, audience, platforms, duration_days, tone, language, cta, angles)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            campaign_name,
            objective[:200],
            audience[:500],
            json.dumps(platforms),
            duration_days,
            tone[:100],
            language[:50],
            cta[:300],
            json.dumps(angles or [])
        ))
        campaign_id = cur.lastrowid
        db.commit()

        # Generate drafts using active AI provider
        provider = get_ai_provider()
        campaign_data = {
            'id': campaign_id,
            'name': campaign_name,
            'objective': objective,
            'audience': audience,
            'platforms': platforms,
            'duration_days': duration_days,
            'tone': tone,
            'language': language,
            'cta': cta
        }
        drafts = provider.generate_campaign(dict(project), campaign_data, brief)

        now = datetime.utcnow()
        for item in drafts:
            if item['platform'] not in platforms:
                continue
            offset = item.get('scheduled_offset_days', 0)
            scheduled_date = (now + timedelta(days=offset)).strftime('%Y-%m-%d 10:00:00')
            project_link = project['website_url'] or project['repository_url'] or ''

            db.execute("""
                INSERT INTO content_assets (
                    campaign_id, platform, format, hook, body, cta,
                    creative_brief, project_link, verification_notes,
                    status, scheduled_for
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_review', ?)
            """, (
                campaign_id,
                item['platform'],
                item['format'],
                item['hook'],
                item['body'],
                item.get('cta', cta),
                item.get('creative_brief', ''),
                project_link,
                item.get('verification_notes', ''),
                scheduled_date
            ))

        # Seed initial distribution targets for Reddit / community outreach
        if 'Reddit' in platforms:
            default_subreddits = [
                ('r/SideProject', 'https://reddit.com/r/SideProject', 'Be transparent that it is a personal project. Check monthly self-promo guidelines.'),
                ('r/webdev', 'https://reddit.com/r/webdev', 'Focus on technical architecture and lessons. Do not spam links.'),
                ('r/learnprogramming', 'https://reddit.com/r/learnprogramming', 'Provide value and answer beginner technical questions.')
            ]
            for sub, url, rules in default_subreddits:
                db.execute("""
                    INSERT INTO distribution_targets (campaign_id, platform, target_name, url, rules_summary, status)
                    VALUES (?, 'Reddit', ?, ?, ?, 'pending')
                """, (campaign_id, sub, url, rules))

        db.execute("""
            INSERT INTO audit_events (entity_type, entity_id, action, details)
            VALUES (?, ?, ?, ?)
        """, ('campaign', campaign_id, 'generated', f"Generated {len(drafts)} drafts with {provider.__class__.__name__}"))
        db.commit()

        return CampaignService.get_campaign_by_id(campaign_id)

    @staticmethod
    def get_assets(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        db = get_db()
        query = """
            SELECT a.*, c.name as campaign_name, p.name as project_name
            FROM content_assets a
            JOIN campaigns c ON c.id = a.campaign_id
            JOIN projects p ON p.id = c.project_id
            WHERE 1=1
        """
        params = []
        if filters:
            if filters.get('campaign_id'):
                query += " AND a.campaign_id = ?"
                params.append(filters['campaign_id'])
            if filters.get('platform'):
                query += " AND a.platform = ?"
                params.append(filters['platform'])
            if filters.get('status'):
                query += " AND a.status = ?"
                params.append(filters['status'])

        query += " ORDER BY a.created_at DESC"
        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def edit_asset(asset_id: int, hook: str, body: str, cta: Optional[str] = None, creative_brief: Optional[str] = None, scheduled_for: Optional[str] = None) -> Dict[str, Any]:
        db = get_db()
        asset = db.execute("SELECT * FROM content_assets WHERE id = ?", (asset_id,)).fetchone()
        if not asset:
            raise ValueError("Asset not found.")

        hook = (hook or '').strip()
        body = (body or '').strip()
        if not hook or not body:
            raise ValueError("Hook and content body cannot be empty.")

        text_changed = (hook != asset['hook'] or body != asset['body'])
        if text_changed:
            # Save prior version to content_versions
            db.execute(
                "INSERT INTO content_versions (asset_id, hook, body) VALUES (?, ?, ?)",
                (asset_id, asset['hook'], asset['body'])
            )

        # Mandatory rule: If an approved asset is edited, return it to needs_review
        status = asset['status']
        if text_changed and status == 'approved':
            status = 'needs_review'

        cta_val = cta.strip() if cta is not None else asset['cta']
        brief_val = creative_brief.strip() if creative_brief is not None else asset['creative_brief']
        sched_val = scheduled_for if scheduled_for else asset['scheduled_for']

        db.execute("""
            UPDATE content_assets
            SET hook = ?, body = ?, cta = ?, creative_brief = ?, scheduled_for = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (hook[:500], body[:10000], cta_val[:300], brief_val[:1000], sched_val, status, asset_id))

        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('asset', asset_id, 'edited', f"Edited asset. Status is now {status}")
        )
        db.commit()

        row = db.execute("SELECT a.*, c.name as campaign_name, p.name as project_name FROM content_assets a JOIN campaigns c ON c.id=a.campaign_id JOIN projects p ON p.id=c.project_id WHERE a.id=?", (asset_id,)).fetchone()
        return dict(row)

    @staticmethod
    def set_asset_status(asset_id: int, new_status: str) -> Dict[str, Any]:
        if new_status not in STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {', '.join(STATUSES)}")

        db = get_db()
        asset = db.execute("SELECT * FROM content_assets WHERE id = ?", (asset_id,)).fetchone()
        if not asset:
            raise ValueError("Asset not found.")

        current = asset['status']

        # Enforce approval workflow rules
        if new_status in {'approved', 'rejected'} and current not in {'needs_review', 'draft', 'rejected', 'approved'}:
            raise ValueError(f"Cannot transition asset from '{current}' to '{new_status}'.")

        if new_status in {'queued', 'published'} and current != 'approved':
            raise ValueError("Asset must be approved before it can be scheduled or marked published.")

        db.execute("UPDATE content_assets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, asset_id))

        # If approved or queued, ensure scheduled_posts record exists
        if new_status in {'approved', 'queued'}:
            sched_time = asset['scheduled_for'] or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            existing_post = db.execute("SELECT id FROM scheduled_posts WHERE asset_id = ?", (asset_id,)).fetchone()
            if not existing_post:
                db.execute(
                    "INSERT INTO scheduled_posts (asset_id, platform, scheduled_for, status) VALUES (?, ?, ?, 'scheduled')",
                    (asset_id, asset['platform'], sched_time)
                )

        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('asset', asset_id, 'status_changed', f"Transitioned from {current} to {new_status}")
        )
        db.commit()

        row = db.execute("SELECT a.*, c.name as campaign_name, p.name as project_name FROM content_assets a JOIN campaigns c ON c.id=a.campaign_id JOIN projects p ON p.id=c.project_id WHERE a.id=?", (asset_id,)).fetchone()
        return dict(row)

    @staticmethod
    def regenerate_asset(asset_id: int, instruction: str) -> Dict[str, Any]:
        db = get_db()
        asset = db.execute("""
            SELECT a.*, p.name as project_name, p.description as project_description,
                   p.website_url, p.repository_url
            FROM content_assets a
            JOIN campaigns c ON c.id = a.campaign_id
            JOIN projects p ON p.id = c.project_id
            WHERE a.id = ?
        """, (asset_id,)).fetchone()
        if not asset:
            raise ValueError("Asset not found.")

        # Save existing version
        db.execute(
            "INSERT INTO content_versions (asset_id, hook, body) VALUES (?, ?, ?)",
            (asset_id, asset['hook'], asset['body'])
        )

        project_data = {
            'name': asset['project_name'],
            'description': asset['project_description'],
            'website_url': asset['website_url'],
            'repository_url': asset['repository_url']
        }

        provider = get_ai_provider()
        regen = provider.regenerate_asset(project_data, dict(asset), instruction)

        # Regenerated draft always returns to needs_review
        db.execute("""
            UPDATE content_assets
            SET hook = ?, body = ?, cta = ?, creative_brief = ?, verification_notes = ?,
                status = 'needs_review', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            regen['hook'][:500],
            regen['body'][:10000],
            regen.get('cta', asset['cta'])[:300],
            regen.get('creative_brief', asset['creative_brief'])[:1000],
            regen.get('verification_notes', asset['verification_notes'])[:500],
            asset_id
        ))

        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('asset', asset_id, 'regenerated', f"Regenerated with instruction: '{instruction}'")
        )
        db.commit()

        row = db.execute("SELECT a.*, c.name as campaign_name, p.name as project_name FROM content_assets a JOIN campaigns c ON c.id=a.campaign_id JOIN projects p ON p.id=c.project_id WHERE a.id=?", (asset_id,)).fetchone()
        return dict(row)

    @staticmethod
    def get_asset_versions(asset_id: int) -> List[Dict[str, Any]]:
        db = get_db()
        rows = db.execute("SELECT * FROM content_versions WHERE asset_id = ? ORDER BY created_at DESC", (asset_id,)).fetchall()
        return [dict(r) for r in rows]
