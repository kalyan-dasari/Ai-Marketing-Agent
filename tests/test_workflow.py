import os
import tempfile
import unittest
import json
from app import create_app
from app.services.security import is_safe_url, is_allowed_file
from app.providers.mock import MockProvider
from app.providers.local_llm import LocalLLMProvider

class WorkflowTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix='.sqlite3')
        os.close(handle)
        self.app = create_app({'TESTING': True, 'DATABASE': self.path, 'SECRET_KEY': 'test-secret'})
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_create_generate_edit_approve_reject_and_reload(self):
        # 1. Create project
        res_proj = self.client.post('/api/v1/projects', json={
            'name': 'Reach demo',
            'description': 'A tool that helps makers share their projects across LinkedIn, Instagram, and Reddit.'
        })
        self.assertEqual(res_proj.status_code, 201)
        project_id = res_proj.json['id']
        self.assertIsNotNone(res_proj.json.get('brief'))

        # 2. Generate campaign
        res_camp = self.client.post('/api/v1/campaigns', json={
            'project_id': project_id,
            'duration_days': 14,
            'platforms': ['LinkedIn', 'Instagram', 'Reddit']
        })
        self.assertEqual(res_camp.status_code, 201)
        assets = res_camp.json['assets']
        self.assertTrue(len(assets) >= 3)
        platforms = {a['platform'] for a in assets}
        self.assertEqual(platforms, {'LinkedIn', 'Instagram', 'Reddit'})

        # 3. Edit asset
        first = assets[0]
        res_edit = self.client.patch(f"/api/v1/assets/{first['id']}", json={
            'hook': 'A more personal opening hook',
            'body': first['body'] + '\n\nAdded verified context.'
        })
        self.assertEqual(res_edit.status_code, 200)
        self.assertEqual(res_edit.json['status'], 'needs_review')
        self.assertEqual(res_edit.json['hook'], 'A more personal opening hook')

        # 4. Approve asset
        res_app = self.client.post(f"/api/v1/assets/{first['id']}/status", json={'status': 'approved'})
        self.assertEqual(res_app.status_code, 200)
        self.assertEqual(res_app.json['status'], 'approved')

        # 5. Editing an approved asset MUST revert it to needs_review
        res_edit2 = self.client.patch(f"/api/v1/assets/{first['id']}", json={
            'hook': 'Changed after approval',
            'body': first['body']
        })
        self.assertEqual(res_edit2.status_code, 200)
        self.assertEqual(res_edit2.json['status'], 'needs_review')

        # 6. Reject second asset
        second = assets[1]
        res_rej = self.client.post(f"/api/v1/assets/{second['id']}/status", json={'status': 'rejected'})
        self.assertEqual(res_rej.status_code, 200)
        self.assertEqual(res_rej.json['status'], 'rejected')

        # 7. Reload assets and verify persistence
        res_all = self.client.get('/api/v1/assets')
        self.assertEqual(res_all.status_code, 200)
        self.assertTrue(len(res_all.json) >= 3)

        # 8. Render main web page
        res_web = self.client.get('/')
        self.assertEqual(res_web.status_code, 200)

    def test_cannot_publish_without_approval(self):
        proj = self.client.post('/api/v1/projects', json={'name': 'Gate Test', 'description': 'Safety gate test.'}).json
        camp = self.client.post('/api/v1/campaigns', json={'project_id': proj['id']}).json
        asset = camp['assets'][0]

        # Cannot publish while in needs_review
        res_fail = self.client.post(f"/api/v1/assets/{asset['id']}/status", json={'status': 'published'})
        self.assertEqual(res_fail.status_code, 400)

        # Approve first
        res_ok = self.client.post(f"/api/v1/assets/{asset['id']}/status", json={'status': 'approved'})
        self.assertEqual(res_ok.status_code, 200)

        # Now queued or published is valid
        res_pub = self.client.post(f"/api/v1/assets/{asset['id']}/status", json={'status': 'published'})
        self.assertEqual(res_pub.status_code, 200)

    def test_project_brief_and_file_upload(self):
        proj = self.client.post('/api/v1/projects', json={
            'name': 'StudEarn Test',
            'description': 'Student services marketplace for campus requests and peer assistance.',
            'website_url': 'https://www.studearning.tech/'
        }).json
        project_id = proj['id']

        # Upload a README document
        readme_content = """# StudEarn
StudEarn connects students on campus.
- Service request workflow
- Peer-to-peer messaging
- Escrow protection
"""
        res_upload = self.client.post(f"/api/v1/projects/{project_id}/sources/upload", json={
            'filename': 'README.md',
            'content': readme_content
        })
        self.assertEqual(res_upload.status_code, 201)

        # Reanalyze brief
        res_brief = self.client.post(f"/api/v1/projects/{project_id}/analyze")
        self.assertEqual(res_brief.status_code, 200)
        brief = res_brief.json
        self.assertEqual(brief['name'], 'StudEarn Test')
        self.assertTrue(len(brief['verified_features']) >= 1)

    def test_regeneration_and_version_history(self):
        proj = self.client.post('/api/v1/projects', json={'name': 'Regen Demo', 'description': 'Testing regeneration.'}).json
        camp = self.client.post('/api/v1/campaigns', json={'project_id': proj['id']}).json
        asset = camp['assets'][0]

        # Regenerate with technical instruction
        res_regen = self.client.post(f"/api/v1/assets/{asset['id']}/regenerate", json={
            'instruction': 'Make it more technical and focus on architecture'
        })
        self.assertEqual(res_regen.status_code, 200)
        self.assertEqual(res_regen.json['status'], 'needs_review')

        # Check version history
        res_hist = self.client.get(f"/api/v1/assets/{asset['id']}/versions")
        self.assertEqual(res_hist.status_code, 200)
        self.assertTrue(len(res_hist.json) >= 1)

    def test_distribution_targets_and_manual_sharing(self):
        proj = self.client.post('/api/v1/projects', json={'name': 'Dist Demo', 'description': 'Testing distribution.'}).json
        camp = self.client.post('/api/v1/campaigns', json={'project_id': proj['id']}).json

        # Check auto-seeded targets
        res_targets = self.client.get(f"/api/v1/distribution/targets?campaign_id={camp['id']}")
        self.assertEqual(res_targets.status_code, 200)
        targets = res_targets.json
        self.assertTrue(len(targets) >= 1)

        # Mark first target as shared
        first_target = targets[0]
        res_share = self.client.post(f"/api/v1/distribution/targets/{first_target['id']}/shared", json={
            'live_url': 'https://reddit.com/r/SideProject/comments/12345/test',
            'notes': 'Positive engagement from 10 builders.'
        })
        self.assertEqual(res_share.status_code, 200)
        self.assertEqual(res_share.json['status'], 'shared')
        self.assertEqual(res_share.json['live_url'], 'https://reddit.com/r/SideProject/comments/12345/test')

    def test_metrics_and_evidence_based_recommendations(self):
        proj = self.client.post('/api/v1/projects', json={'name': 'Metric Demo', 'description': 'Testing metrics.'}).json
        camp = self.client.post('/api/v1/campaigns', json={'project_id': proj['id']}).json
        asset = camp['assets'][0]

        # Record metrics
        res_metric = self.client.post('/api/v1/analytics/metrics', json={
            'asset_id': asset['id'],
            'impressions': 1200,
            'reach': 950,
            'engagements': 64,
            'clicks': 28,
            'notes': 'Solid discussion in comments'
        })
        self.assertEqual(res_metric.status_code, 201)

        # Fetch analytics summary
        res_sum = self.client.get('/api/v1/analytics/summary')
        self.assertEqual(res_sum.status_code, 200)
        data = res_sum.json
        self.assertEqual(data['totals']['impressions'], 1200)
        self.assertEqual(data['totals']['engagements'], 64)
        self.assertTrue(len(data['recommendations']) >= 1)

    def test_security_ssrf_validator(self):
        # Localhost and private IPs must be blocked
        self.assertFalse(is_safe_url('http://localhost:5000')[0])
        self.assertFalse(is_safe_url('http://127.0.0.1:8080')[0])
        self.assertFalse(is_safe_url('http://10.0.0.1')[0])
        self.assertFalse(is_safe_url('http://192.168.1.1')[0])
        self.assertFalse(is_safe_url('file:///etc/passwd')[0])
        self.assertFalse(is_safe_url('gopher://test.com')[0])

        # Allowed files
        self.assertTrue(is_allowed_file('README.md'))
        self.assertTrue(is_allowed_file('notes.txt'))
        self.assertFalse(is_allowed_file('malicious.exe'))
        self.assertFalse(is_allowed_file('script.sh'))

    def test_settings_and_local_llm_fallback(self):
        # Update settings
        res_set = self.client.post('/api/v1/settings', json={
            'ai_provider': 'mock',
            'ollama_model': 'mistral'
        })
        self.assertEqual(res_set.status_code, 200)
        self.assertEqual(res_set.json['ollama_model'], 'mistral')

        # Test local LLM fallback (when offline)
        provider = LocalLLMProvider(endpoint_url='http://127.0.0.1:9999', model='llama3')
        connected, msg = provider.test_connection()
        self.assertFalse(connected)
        # Provider fallback still generates safe drafts
        drafts = provider.generate_campaign(
            {'name': 'Offline Test', 'description': 'Testing fallback'},
            {'platforms': ['LinkedIn', 'Instagram']}
        )
        self.assertTrue(len(drafts) >= 2)

    def test_groq_provider_and_settings(self):
        from app.providers.groq_provider import GroqProvider
        # Test GroqProvider with configured key
        key = os.environ.get('GROQ_API_KEY')
        if key:
            provider = GroqProvider(api_key=key, model='openai/gpt-oss-120b')
            connected, msg = provider.test_connection()
            self.assertTrue(connected)

            # Test API test endpoint
            res_test = self.client.post('/api/v1/settings/test-groq', json={
                'groq_api_key': key,
                'groq_model': 'openai/gpt-oss-120b'
            })
            self.assertEqual(res_test.status_code, 200)
            self.assertTrue(res_test.json['success'])

        # Test invalid key handling
        bad_provider = GroqProvider(api_key='gsk_invalid_test_key')
        connected_bad, msg_bad = bad_provider.test_connection()
        self.assertFalse(connected_bad)

        # Test fallback generation
        fallback_drafts = bad_provider.generate_campaign(
            {'name': 'Fallback Test', 'description': 'Testing Groq fallback'},
            {'platforms': ['LinkedIn', 'Reddit']}
        )
        self.assertTrue(len(fallback_drafts) >= 2)

if __name__ == '__main__':
    unittest.main()

