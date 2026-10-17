from typing import Dict, Any, List, Optional
from ..db import get_db
from ..providers.factory import get_ai_provider

class AnalyticsService:
    @staticmethod
    def record_metrics(
        asset_id: int,
        impressions: int = 0,
        reach: int = 0,
        engagements: int = 0,
        clicks: int = 0,
        video_views: int = 0,
        conversions: int = 0,
        notes: str = ''
    ) -> Dict[str, Any]:
        db = get_db()
        asset = db.execute("SELECT id, status FROM content_assets WHERE id = ?", (asset_id,)).fetchone()
        if not asset:
            raise ValueError("Asset not found.")

        cur = db.execute("""
            INSERT INTO post_metrics (asset_id, impressions, reach, engagements, clicks, video_views, conversions, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asset_id,
            max(0, int(impressions or 0)),
            max(0, int(reach or 0)),
            max(0, int(engagements or 0)),
            max(0, int(clicks or 0)),
            max(0, int(video_views or 0)),
            max(0, int(conversions or 0)),
            notes.strip()[:500]
        ))
        
        # If asset was approved, update to published since performance metrics are being logged
        if asset['status'] == 'approved':
            db.execute("UPDATE content_assets SET status = 'published', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (asset_id,))

        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('metric', cur.lastrowid, 'recorded', f"Recorded metrics for asset {asset_id}: {impressions} impressions, {engagements} engagements")
        )
        db.commit()

        row = db.execute("SELECT * FROM post_metrics WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    @staticmethod
    def get_summary() -> Dict[str, Any]:
        db = get_db()
        # Fetch raw records joined with asset details
        rows = db.execute("""
            SELECT m.*, a.platform, a.format, a.hook, c.name as campaign_name, p.name as project_name
            FROM post_metrics m
            JOIN content_assets a ON a.id = m.asset_id
            JOIN campaigns c ON c.id = a.campaign_id
            JOIN projects p ON p.id = c.project_id
            ORDER BY m.recorded_at DESC
        """).fetchall()

        metric_records = [dict(r) for r in rows]

        total_impressions = sum(r['impressions'] for r in metric_records)
        total_reach = sum(r['reach'] for r in metric_records)
        total_engagements = sum(r['engagements'] for r in metric_records)
        total_clicks = sum(r['clicks'] for r in metric_records)
        total_views = sum(r['video_views'] for r in metric_records)
        total_conversions = sum(r['conversions'] for r in metric_records)

        avg_engagement_rate = (total_engagements / total_impressions * 100) if total_impressions > 0 else 0.0
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0

        # Platform breakdown
        by_platform: Dict[str, Dict[str, Any]] = {}
        for r in metric_records:
            p = r['platform']
            if p not in by_platform:
                by_platform[p] = {'impressions': 0, 'engagements': 0, 'clicks': 0, 'posts_tracked': 0}
            by_platform[p]['impressions'] += r['impressions']
            by_platform[p]['engagements'] += r['engagements']
            by_platform[p]['clicks'] += r['clicks']
            by_platform[p]['posts_tracked'] += 1

        for p, data in by_platform.items():
            data['engagement_rate'] = round((data['engagements'] / data['impressions'] * 100), 1) if data['impressions'] > 0 else 0.0
            data['ctr'] = round((data['clicks'] / data['impressions'] * 100), 1) if data['impressions'] > 0 else 0.0

        # Format breakdown
        by_format: Dict[str, Dict[str, Any]] = {}
        for r in metric_records:
            fmt = r['format']
            if fmt not in by_format:
                by_format[fmt] = {'impressions': 0, 'engagements': 0, 'clicks': 0, 'count': 0}
            by_format[fmt]['impressions'] += r['impressions']
            by_format[fmt]['engagements'] += r['engagements']
            by_format[fmt]['clicks'] += r['clicks']
            by_format[fmt]['count'] += 1

        for fmt, data in by_format.items():
            data['engagement_rate'] = round((data['engagements'] / data['impressions'] * 100), 1) if data['impressions'] > 0 else 0.0

        # Generate AI recommendations from actual data
        provider = get_ai_provider()
        recommendations = provider.generate_recommendations(metric_records)

        return {
            'totals': {
                'impressions': total_impressions,
                'reach': total_reach,
                'engagements': total_engagements,
                'clicks': total_clicks,
                'video_views': total_views,
                'conversions': total_conversions,
                'engagement_rate': round(avg_engagement_rate, 2),
                'ctr': round(avg_ctr, 2),
                'posts_tracked': len(metric_records)
            },
            'by_platform': by_platform,
            'by_format': by_format,
            'recent_logs': metric_records[:10],
            'recommendations': recommendations
        }
