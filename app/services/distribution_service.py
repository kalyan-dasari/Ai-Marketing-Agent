import datetime
from typing import Dict, Any, List, Optional
from ..db import get_db

class DistributionService:
    @staticmethod
    def get_targets(campaign_id: Optional[int] = None) -> List[Dict[str, Any]]:
        db = get_db()
        if campaign_id:
            rows = db.execute("""
                SELECT d.*, c.name as campaign_name, p.name as project_name
                FROM distribution_targets d
                JOIN campaigns c ON c.id = d.campaign_id
                JOIN projects p ON p.id = c.project_id
                WHERE d.campaign_id = ?
                ORDER BY d.created_at DESC
            """, (campaign_id,)).fetchall()
        else:
            rows = db.execute("""
                SELECT d.*, c.name as campaign_name, p.name as project_name
                FROM distribution_targets d
                JOIN campaigns c ON c.id = d.campaign_id
                JOIN projects p ON p.id = c.project_id
                ORDER BY d.created_at DESC
            """).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def add_target(campaign_id: int, platform: str, target_name: str, url: str, rules_summary: str = '') -> Dict[str, Any]:
        db = get_db()
        cur = db.execute("""
            INSERT INTO distribution_targets (campaign_id, platform, target_name, url, rules_summary, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (campaign_id, platform, target_name.strip(), url.strip(), rules_summary.strip()))
        db.commit()
        return {"id": cur.lastrowid, "target_name": target_name, "status": "pending"}

    @staticmethod
    def mark_shared(target_id: int, live_url: str = '', notes: str = '') -> Dict[str, Any]:
        db = get_db()
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        db.execute("""
            UPDATE distribution_targets
            SET status = 'shared', live_url = ?, notes = ?, shared_at = ?
            WHERE id = ?
        """, (live_url.strip(), notes.strip(), now, target_id))
        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('distribution_target', target_id, 'manual_share_recorded', f"Live URL: {live_url}")
        )
        db.commit()
        row = db.execute("SELECT * FROM distribution_targets WHERE id = ?", (target_id,)).fetchone()
        return dict(row)

    @staticmethod
    def attempt_auto_publish(asset_id: int) -> tuple[bool, str]:
        """
        Placeholder / Safety Gate for Automated Social Publishing.
        Returns False and clear guidance because zero-budget offline version requires manual sharing.
        Never pretends to publish when unconfigured.
        """
        return False, "Automated social publishing integration is currently unconfigured. Copy your approved text and share manually according to community guidelines."
