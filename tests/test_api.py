import os
import json
import tempfile
import unittest
from werkzeug.security import generate_password_hash

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['FLASK_DEBUG'] = '0'
os.environ['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='uploads_')

from app import app
from models import db, User, AnalysisSession, Student, AnalysisResult

class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config['TESTING'] = True
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(
                username='testuser',
                email='test@example.com',
                faculty_name='Tester',
                password_hash=generate_password_hash('password123')
            )
            db.session.add(user)
            db.session.commit()

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            self.user = User.query.filter_by(username='testuser').first()

    def login(self):
        return self.client.post('/login', data={'username': 'testuser', 'password': 'password123'}, follow_redirects=True)

    def test_health_endpoint(self):
        r = self.client.get('/health')
        self.assertIn(r.status_code, (200, 503))
        data = json.loads(r.data.decode())
        self.assertIn('db', data)
        self.assertIn('upload_dir', data)

    def test_session_api_unauthorized(self):
        r = self.client.get('/api/session/1')
        self.assertEqual(r.status_code, 302)

    def test_session_api_happy_path(self):
        self.login()
        with self.app.app_context():
            session = AnalysisSession(user_id=self.user.id, session_name='S1', subject_name='Physics')
            db.session.add(session)
            db.session.commit()
            session_id = session.id
            s1 = Student(session_id=session.id, name='A', reg_number='R1', exam_number='E1')
            s2 = Student(session_id=session.id, name='B', reg_number='R2', exam_number='E2')
            db.session.add_all([s1, s2])
            db.session.commit()
            res = AnalysisResult(
                session_id=session_id,
                script1_id=s1.id,
                script2_id=s2.id,
                similarity_score=0.75,
                detection_method='text_similarity',
                suspicious_lines=json.dumps([{'line_number_script1':1,'line_number_script2':1,'text_script1':'x','text_script2':'y','similarity':0.8}]),
                recommendation='Check'
            )
            db.session.add(res)
            db.session.commit()
        r = self.client.get(f'/api/session/{session_id}')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data.decode())
        self.assertEqual(data['session']['id'], session_id)
        self.assertEqual(len(data['students']), 2)
        self.assertEqual(len(data['results']), 1)

    def test_session_api_forbidden_other_user(self):
        self.login()
        with self.app.app_context():
            other = User(
                username='other',
                email='other@example.com',
                faculty_name='Other',
                password_hash=generate_password_hash('password123')
            )
            db.session.add(other)
            db.session.commit()
            session = AnalysisSession(user_id=other.id, session_name='S2', subject_name='Chemistry')
            db.session.add(session)
            db.session.commit()
            other_session_id = session.id
        r = self.client.get(f'/api/session/{other_session_id}')
        self.assertEqual(r.status_code, 403)

if __name__ == '__main__':
    unittest.main()
