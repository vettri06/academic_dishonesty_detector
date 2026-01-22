from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import hashlib

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    faculty_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalysisSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_name = db.Column(db.String(200), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('sessions', lazy=True))
    students = db.relationship('Student', backref='session', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('AnalysisResult', backref='session', lazy=True, cascade='all, delete-orphan')

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_session.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    reg_number = db.Column(db.String(50), nullable=False)
    exam_number = db.Column(db.String(50), nullable=False)
    answer_script_path = db.Column(db.String(500))  # Store individual file path
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_session.id'), nullable=False)
    script1_id = db.Column(db.Integer, nullable=False)
    script2_id = db.Column(db.Integer, nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    detection_method = db.Column(db.String(100), nullable=False)
    suspicious_lines = db.Column(db.Text)
    recommendation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)