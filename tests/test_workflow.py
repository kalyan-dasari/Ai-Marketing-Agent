import os
import tempfile
import unittest
from app import create_app

class WorkflowTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix='.sqlite3')
        os.close(handle)
        self.app = create_app({'TESTING': True, 'DATABASE': self.path, 'SECRET_KEY': 'test'})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.path)

    def test_create_generate_edit_approve_reject_and_reload(self):
        project = self.client.post('/api/v1/projects', json={'name':'Reach demo','description':'A tool that helps makers share their projects.'})
        self.assertEqual(project.status_code, 201)
        project_id = project.json['id']
        generated = self.client.post('/api/v1/campaigns', json={'project_id':project_id})
        self.assertEqual(generated.status_code, 201)
        self.assertEqual({a['platform'] for a in generated.json['assets']}, {'LinkedIn','Instagram','Reddit'})
        first = generated.json['assets'][0]
        edited = self.client.patch(f"/api/v1/assets/{first['id']}", json={'hook':'A more personal opening','body':first['body']+'\n\nAdded context.'})
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json['status'], 'needs_review')
        approved = self.client.post(f"/api/v1/assets/{first['id']}/status", json={'status':'approved'})
        self.assertEqual(approved.json['status'], 'approved')
        rejected = self.client.post(f"/api/v1/assets/{generated.json['assets'][1]['id']}/status", json={'status':'rejected'})
        self.assertEqual(rejected.json['status'], 'rejected')
        reloaded = self.client.get('/api/v1/assets')
        self.assertEqual(len(reloaded.json), 3)
        self.assertEqual(next(a for a in reloaded.json if a['id']==first['id'])['hook'], 'A more personal opening')
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_cannot_publish_without_approval(self):
        project=self.client.post('/api/v1/projects',json={'name':'Test','description':'A description.'}).json
        asset=self.client.post('/api/v1/campaigns',json={'project_id':project['id']}).json['assets'][0]
        response=self.client.post(f"/api/v1/assets/{asset['id']}/status",json={'status':'published'})
        self.assertEqual(response.status_code,400)

if __name__ == '__main__': unittest.main()
