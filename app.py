from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AnalysisSession, Student, AnalysisResult
from academic_detector import AcademicDishonestyDetector
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
import os
import json
import io
import sqlite3

app = Flask(__name__, template_folder='Templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'danger'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('instance', exist_ok=True)

def init_db():
    """Initialize database with proper schema"""
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Create demo user
        if User.query.count() == 0:
            demo_user = User(
                username='admin',
                email='admin@academic.edu',
                faculty_name='Administrator',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(demo_user)
            db.session.commit()
            print("=" * 50)
            print("DATABASE INITIALIZED SUCCESSFULLY!")
            print("Demo user created:")
            print("Username: admin")
            print("Password: admin123")
            print("=" * 50)

def check_and_fix_database():
    """Check if database schema is correct and fix if needed"""
    try:
        # Try to query a student to see if schema is correct
        test_student = Student.query.first()
        return True
    except Exception as e:
        print(f"Database schema issue detected: {e}")
        print("Reinitializing database...")
        init_db()
        return False

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate form data
        if not username or not password:
            flash('Please fill in all fields', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.faculty_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        faculty_name = request.form.get('faculty_name', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validate form data
        if not all([username, email, faculty_name, password, confirm_password]):
            flash('Please fill in all fields', 'danger')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'danger')
            return render_template('signup.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('signup.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            faculty_name=faculty_name,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('signup.html')
    
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    recent_sessions = AnalysisSession.query.filter_by(user_id=current_user.id)\
        .order_by(AnalysisSession.created_at.desc()).limit(5).all()
    
    total_sessions = AnalysisSession.query.filter_by(user_id=current_user.id).count()
    
    return render_template('dashboard.html', 
                         faculty_name=current_user.faculty_name,
                         recent_sessions=recent_sessions,
                         total_sessions=total_sessions)

@app.route('/history')
@login_required
def history():
    sessions = AnalysisSession.query.filter_by(user_id=current_user.id)\
        .order_by(AnalysisSession.created_at.desc()).all()
    return render_template('history.html', sessions=sessions)

@app.route('/malpractice_check', methods=['GET', 'POST'])
@login_required
def malpractice_check():
    if request.method == 'POST':
        session_name = request.form.get('session_name', '').strip()
        subject_name = request.form.get('subject_name', '').strip()
        num_students = request.form.get('num_students', '2', type=int)
        
        if not session_name or not subject_name:
            flash('Please fill in all required fields', 'danger')
            return render_template('malpractice_check.html')
        
        if num_students < 2 or num_students > 20:
            flash('Number of students must be between 2 and 20', 'danger')
            return render_template('malpractice_check.html')
        
        # Create new analysis session
        session = AnalysisSession(
            user_id=current_user.id,
            session_name=session_name,
            subject_name=subject_name
        )
        db.session.add(session)
        db.session.commit()
        
        flash('Analysis session created successfully! Please add student details.', 'success')
        return redirect(url_for('upload_scripts', session_id=session.id, num_students=num_students))
    
    return render_template('malpractice_check.html')

@app.route('/upload_scripts/<int:session_id>', methods=['GET', 'POST'])
@login_required
def upload_scripts(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    
    if request.method == 'POST':
        # Get number of students from form
        num_students = int(request.form.get('num_students', 2))
        
        # Process student data and file uploads
        students_data = []
        uploaded_files = []
        file_errors = []
        
        for i in range(1, num_students + 1):
            name = request.form.get(f'student_name_{i}', '').strip()
            reg_number = request.form.get(f'reg_number_{i}', '').strip()
            exam_number = request.form.get(f'exam_number_{i}', '').strip()
            
            if name and reg_number and exam_number:
                student_data = {
                    'name': name,
                    'reg_number': reg_number,
                    'exam_number': exam_number,
                    'file': request.files.get(f'answer_script_{i}')
                }
                students_data.append(student_data)
        
        if not students_data:
            flash('Please add at least one student with all details', 'danger')
            return redirect(url_for('upload_scripts', session_id=session_id, num_students=num_students))
        
        # Save students to database and handle file uploads
        for i, student_data in enumerate(students_data, 1):
            student = Student(
                session_id=session_id,
                name=student_data['name'],
                reg_number=student_data['reg_number'],
                exam_number=student_data['exam_number']
            )
            db.session.add(student)
            
            # Handle individual file upload for this student
            file = student_data['file']
            if file and file.filename:
                # Check file size (10MB limit for upload)
                file.seek(0, 2)  # Seek to end to get size
                file_size = file.tell()
                file.seek(0)  # Reset file pointer
                
                if file_size > 10 * 1024 * 1024:  # 10MB
                    file_errors.append(f"{file.filename} for {student_data['name']} exceeds 10MB limit")
                    continue
                
                # Save file with student ID for unique identification
                file_extension = os.path.splitext(file.filename)[1]
                # Get student ID after commit
                db.session.flush()
                filename = f"{session_id}_{student.id}_{student_data['name'].replace(' ', '_')}{file_extension}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                uploaded_files.append({
                    'filename': filename,
                    'student_name': student_data['name'],
                    'student_id': student.id
                })
                
                # Update student record with file path
                student.answer_script_path = file_path
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving student data: {str(e)}', 'danger')
            return redirect(url_for('upload_scripts', session_id=session_id, num_students=num_students))
        
        # Show upload results
        if uploaded_files:
            flash(f'Successfully uploaded {len(uploaded_files)} files and saved {len(students_data)} students!', 'success')
        if file_errors:
            for error in file_errors:
                flash(error, 'warning')
        
        return redirect(url_for('processing', session_id=session_id))
    
    # Get number of students from previous form or default to 2
    num_students = request.args.get('num_students', 2, type=int)
    return render_template('upload_scripts.html', session=session, num_students=num_students)

@app.route('/processing/<int:session_id>')
@login_required
def processing(session_id):
    """Render the processing loading screen"""
    session = AnalysisSession.query.get_or_404(session_id)
    return render_template('processing.html', session_id=session_id, session=session)

@app.route('/analyze_scripts/<int:session_id>')
@login_required
def analyze_scripts(session_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    session = AnalysisSession.query.get_or_404(session_id)
    students = Student.query.filter_by(session_id=session_id).all()
    
    if not students:
        if is_ajax:
            return jsonify({'status': 'error', 'message': 'No students found for this session'})
        flash('No students found for this session', 'danger')
        return redirect(url_for('upload_scripts', session_id=session_id))
    
    # Initialize detector
    detector = AcademicDishonestyDetector()
    
    # Get file paths from individual student records
    file_paths = []
    valid_students = []
    
    for student in students:
        if student.answer_script_path and os.path.exists(student.answer_script_path):
            file_paths.append(student.answer_script_path)
            valid_students.append(student)
        else:
            print(f"Warning: No answer script found for {student.name}")
    
    if file_paths:
        try:
            api_key_env = os.getenv('OCR_API_KEY')
            API_KEY = api_key_env if api_key_env else 'helloworld'
            if not api_key_env:
                flash('OCR_API_KEY not set; using limited demo OCR key. Results may be incomplete.', 'warning')
            processed_scripts = detector.process_scripts_with_ocr(file_paths, API_KEY)
            
            if processed_scripts:
                # Map processed scripts back to students
                student_id_mapping = {i+1: student.id for i, student in enumerate(valid_students)}
                
                for i, script in enumerate(processed_scripts):
                    if i < len(valid_students):
                        script['student_id'] = valid_students[i].id
                        script['id'] = i + 1  # Reassign IDs based on valid students
                
                # Update answer_scripts with mapped data
                detector.answer_scripts = processed_scripts
                
                # Generate report
                report = detector.generate_comprehensive_report()
                
                # Store results in database
                for result_type, results in report['detection_results'].items():
                    for result in results:
                        if 'script1_id' in result and 'script2_id' in result:
                            # Map script IDs back to student IDs
                            script1_id = result['script1_id']
                            script2_id = result['script2_id']
                            
                            if script1_id in student_id_mapping and script2_id in student_id_mapping:
                                analysis_result = AnalysisResult(
                                    session_id=session_id,
                                    script1_id=student_id_mapping[script1_id],
                                    script2_id=student_id_mapping[script2_id],
                                    similarity_score=result.get('similarity_score', 0),
                                    detection_method=result['detection_method'],
                                    suspicious_lines=json.dumps(result.get('suspicious_lines', [])),
                                    recommendation=result.get('recommendation', 'No specific recommendation')
                                )
                                db.session.add(analysis_result)
                
                db.session.commit()
                flash(f'Analysis completed successfully! Processed {len(processed_scripts)} answer scripts.', 'success')
                
                if is_ajax:
                    return jsonify({'status': 'success', 'redirect_url': url_for('results', session_id=session_id)})
            else:
                allow_demo = os.getenv('ALLOW_DEMO_FALLBACK', '1') == '1'
                if allow_demo:
                    flash('OCR processing failed. Using demo analysis.', 'warning')
                    if is_ajax:
                        return jsonify({'status': 'warning', 'message': 'OCR processing failed. Using demo analysis.', 'redirect_url': url_for('demo_results', session_id=session_id)})
                    return redirect(url_for('demo_results', session_id=session_id))
                else:
                    msg = 'OCR processing failed. Please check OCR_API_KEY and image quality.'
                    if is_ajax:
                        return jsonify({'status': 'error', 'message': msg}), 500
                    flash(msg, 'danger')
                    return redirect(url_for('upload_scripts', session_id=session_id))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Analysis failed: {str(e)}. Using demo analysis.', 'warning')
            if is_ajax:
                 return jsonify({'status': 'error', 'message': f'Analysis failed: {str(e)}', 'redirect_url': url_for('demo_results', session_id=session_id)})
            return redirect(url_for('demo_results', session_id=session_id))
    else:
        allow_demo = os.getenv('ALLOW_DEMO_FALLBACK', '1') == '1'
        if allow_demo:
            flash('No answer scripts uploaded. Using demo analysis.', 'info')
            if is_ajax:
                 return jsonify({'status': 'info', 'message': 'No answer scripts uploaded. Using demo analysis.', 'redirect_url': url_for('demo_results', session_id=session_id)})
            return redirect(url_for('demo_results', session_id=session_id))
        else:
            msg = 'No answer scripts uploaded. Please upload images to run OCR.'
            if is_ajax:
                 return jsonify({'status': 'error', 'message': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('upload_scripts', session_id=session_id))
    
    return redirect(url_for('results', session_id=session_id))

@app.route('/results/<int:session_id>')
@login_required
def results(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    students = Student.query.filter_by(session_id=session_id).all()
    results = AnalysisResult.query.filter_by(session_id=session_id).all()
    
    # Attach parsed suspicious lines for view without mutating DB column
    for result in results:
        parsed = []
        if result.suspicious_lines:
            try:
                parsed = json.loads(result.suspicious_lines)
            except Exception:
                parsed = []
        setattr(result, 'parsed_suspicious_lines', parsed)
    
    return render_template('results.html', 
                         session=session, 
                         students=students, 
                         results=results)

@app.route('/demo_results/<int:session_id>')
@login_required
def demo_results(session_id):
    """Generate demo results for testing"""
    session = AnalysisSession.query.get_or_404(session_id)
    students = Student.query.filter_by(session_id=session_id).all()
    
    # Clear any existing results for this session
    AnalysisResult.query.filter_by(session_id=session_id).delete()
    
    # Create demo results based on actual student count
    demo_results_data = []
    student_count = len(students)
    
    if student_count >= 2:
        # Only create results for actual students, not all possible combinations
        demo_texts = [
            "The fundamental principles of quantum mechanics suggest that particles can exist in multiple states simultaneously until observed.",
            "Therefore, the wave function collapse occurs when a measurement is made, determining the definite state of the particle.",
            "The uncertainty principle was formulated by Heisenberg in 1927, stating the fundamental limit to precision.",
            "Quantum entanglement describes how particles can become correlated in such a way that the state of one particle instantly affects the state of another.",
            "Schrodinger's equation is a fundamental equation in quantum mechanics that describes how the quantum state of a physical system changes with time."
        ]
        
        # Create results for adjacent student pairs (1-2, 2-3, etc.)
        for i in range(student_count - 1):
            script1_id = students[i].id
            script2_id = students[i + 1].id
            
            # Vary similarity scores for realism
            similarity_score = 0.65 + (i * 0.1)  # 65% to 85% similarity
            if similarity_score > 0.9:
                similarity_score = 0.9
            
            # Create suspicious lines based on similarity
            suspicious_lines = []
            if similarity_score > 0.7:
                # High similarity - more matching lines
                line_count = min(3, len(demo_texts))
                for j in range(line_count):
                    suspicious_lines.append({
                        'line_number_script1': j + 1,
                        'line_number_script2': j + 1,
                        'text_script1': demo_texts[j],
                        'text_script2': demo_texts[j],
                        'similarity': 0.9 + (j * 0.02)
                    })
            else:
                # Medium similarity - fewer matching lines
                line_count = min(2, len(demo_texts))
                for j in range(line_count):
                    suspicious_lines.append({
                        'line_number_script1': j + 1,
                        'line_number_script2': j + 1,
                        'text_script1': demo_texts[j],
                        'text_script2': demo_texts[j],
                        'similarity': 0.8 + (j * 0.05)
                    })
            
            # Generate appropriate recommendation
            if similarity_score > 0.8:
                recommendation = '🚨 HIGH RISK: Strong evidence of copying. Multiple suspicious lines detected. Immediate investigation recommended.'
            elif similarity_score > 0.7:
                recommendation = '⚠️ MEDIUM-HIGH RISK: Significant similarities with multiple matching lines. Detailed review required.'
            elif similarity_score > 0.6:
                recommendation = '⚠️ MEDIUM RISK: Notable similarities detected. Further investigation recommended.'
            else:
                recommendation = '📝 LOW-MEDIUM RISK: Some similarities found. Monitor for future assignments.'
            
            demo_result = AnalysisResult(
                session_id=session_id,
                script1_id=script1_id,
                script2_id=script2_id,
                similarity_score=similarity_score,
                detection_method='text_similarity',
                suspicious_lines=json.dumps(suspicious_lines),
                recommendation=recommendation
            )
            demo_results_data.append(demo_result)
    
    # Save demo results to database
    for result in demo_results_data:
        db.session.add(result)
    
    db.session.commit()
    
    # Fetch the saved results
    results = AnalysisResult.query.filter_by(session_id=session_id).all()
    
    # Attach parsed suspicious lines for view without mutating DB column
    for result in results:
        parsed = []
        if result.suspicious_lines:
            try:
                parsed = json.loads(result.suspicious_lines)
            except Exception:
                parsed = []
        setattr(result, 'parsed_suspicious_lines', parsed)
    
    flash(f'Demo analysis completed for {student_count} students!', 'info')
    return render_template('results.html', 
                         session=session, 
                         students=students, 
                         results=results)

@app.route('/generate_report/<int:session_id>')
@login_required
def generate_report(session_id):
    session = AnalysisSession.query.get_or_404(session_id)
    students = Student.query.filter_by(session_id=session_id).all()
    results = AnalysisResult.query.filter_by(session_id=session_id).all()
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"Academic Dishonesty Report - {session.subject_name}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Session info
    info_data = [
        ['Session Name', session.session_name],
        ['Subject', session.subject_name],
        ['Analysis Date', session.created_at.strftime('%Y-%m-%d %H:%M')],
        ['Faculty', current_user.faculty_name],
        ['Total Students', str(len(students))],
        ['Suspicious Pairs', str(len(results))]
    ]
    
    info_table = Table(info_data, colWidths=[200, 300])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Suspected students
    suspected_students = []
    for result in results:
        student1 = next((s for s in students if s.id == result.script1_id), None)
        student2 = next((s for s in students if s.id == result.script2_id), None)
        if student1 and student2:
            suspected_students.append({
                'student1': student1,
                'student2': student2,
                'similarity': result.similarity_score,
                'recommendation': result.recommendation
            })
    
    if suspected_students:
        suspects_title = Paragraph("Suspected Students", styles['Heading2'])
        story.append(suspects_title)
        story.append(Spacer(1, 12))
        
        suspects_data = [['Student 1', 'Reg No', 'Student 2', 'Reg No', 'Similarity %']]
        for suspect in suspected_students:
            suspects_data.append([
                suspect['student1'].name,
                suspect['student1'].reg_number,
                suspect['student2'].name,
                suspect['student2'].reg_number,
                f"{suspect['similarity']*100:.2f}%"
            ])
        
        suspects_table = Table(suspects_data, colWidths=[120, 80, 120, 80, 80])
        suspects_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fadbd8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(suspects_table)
        story.append(Spacer(1, 20))
        
        # Recommendations
        rec_title = Paragraph("Recommendations", styles['Heading2'])
        story.append(rec_title)
        story.append(Spacer(1, 12))
        
        for i, suspect in enumerate(suspected_students, 1):
            rec_text = f"Pair {i}: {suspect['recommendation']}"
            rec_para = Paragraph(rec_text, styles['BodyText'])
            story.append(rec_para)
            story.append(Spacer(1, 8))
    
    else:
        no_issues = Paragraph("No significant academic dishonesty detected in this analysis.", styles['Heading2'])
        story.append(no_issues)
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, 
                    download_name=f"academic_report_{session_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mimetype='application/pdf')

@app.route('/api/session/<int:session_id>')
@login_required
def get_session_data(session_id):
    """API endpoint to get session data"""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    students = Student.query.filter_by(session_id=session_id).all()
    results = AnalysisResult.query.filter_by(session_id=session_id).all()
    
    session_data = {
        'session': {
            'id': session.id,
            'name': session.session_name,
            'subject': session.subject_name,
            'created_at': session.created_at.isoformat()
        },
        'students': [{
            'id': s.id,
            'name': s.name,
            'reg_number': s.reg_number,
            'exam_number': s.exam_number
        } for s in students],
        'results': [{
            'id': r.id,
            'script1_id': r.script1_id,
            'script2_id': r.script2_id,
            'similarity_score': r.similarity_score,
            'detection_method': r.detection_method,
            'recommendation': r.recommendation
        } for r in results]
    }
    
    return jsonify(session_data)

@app.route('/delete_session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete an analysis session"""
    session = AnalysisSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('history'))
    
    try:
        # Delete related records
        Student.query.filter_by(session_id=session_id).delete()
        AnalysisResult.query.filter_by(session_id=session_id).delete()
        db.session.delete(session)
        db.session.commit()
        flash('Session deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete session', 'danger')
    
    return redirect(url_for('history'))

@app.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    """Save user theme and background settings"""
    try:
        data = request.get_json()
        # You can save user-specific settings to the database here
        # For now, we'll just return success
        return jsonify({'status': 'success', 'message': 'Settings saved'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/settings/reset', methods=['POST'])
@login_required
def reset_settings():
    """Reset user settings to defaults"""
    try:
        # You can reset user-specific settings here
        return jsonify({'status': 'success', 'message': 'Settings reset to defaults'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/user/profile')
@login_required
def user_profile():
    """User profile page with theme settings"""
    return render_template('profile.html', faculty_name=current_user.faculty_name)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Maximum file size is 10MB.', 'danger')
    return redirect(request.url)

@app.route('/health')
def health():
    status = {'db': False, 'upload_dir': False, 'env': {}, 'ok': False}
    try:
        db.session.execute(db.text('SELECT 1'))
        status['db'] = True
    except Exception:
        status['db'] = False
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        test_path = os.path.join(upload_dir, '.write_test')
        with open(test_path, 'w') as f:
            f.write('ok')
        os.remove(test_path)
        status['upload_dir'] = True
    except Exception:
        status['upload_dir'] = False
    status['env'] = {
        'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', ''),
        'upload_folder': app.config.get('UPLOAD_FOLDER', ''),
        'debug': os.getenv('FLASK_DEBUG', '0')
    }
    status['ok'] = status['db'] and status['upload_dir']
    return jsonify(status), (200 if status['ok'] else 503)

@app.route('/debug/ocr/<path:filename>')
@login_required
def debug_ocr(filename):
    try:
        detector = AcademicDishonestyDetector()
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'file_not_found', 'path': file_path}), 404
        size_kb = round(os.path.getsize(file_path) / 1024, 1)
        api_key = os.getenv('OCR_API_KEY', '')
        processed_file_path = detector.compress_image(file_path) if size_kb > 900 else file_path
        result = detector.ocr_space_file(filename=processed_file_path, language="eng", api_key=api_key)
        text = detector.extract_text(result)
        resp = {
            'file': filename,
            'size_kb': size_kb,
            'used_compressed': processed_file_path != file_path,
            'ocr_exit_code': result.get('OCRExitCode'),
            'is_errored': result.get('IsErroredOnProcessing'),
            'error_message': result.get('ErrorMessage'),
            'parsed_text_len': len(text),
            'parsed_text_head': text[:300]
        }
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({'error': 'exception', 'message': str(e)}), 500

# Database initialization and startup
if __name__ == '__main__':
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = None
        if db_uri.startswith('sqlite:////'):
            db_path = db_uri.replace('sqlite:////', '/', 1)
        elif db_uri.startswith('sqlite:///'):
            db_rel = db_uri.replace('sqlite:///', '', 1)
            db_path = db_rel if os.path.isabs(db_rel) else os.path.join(os.getcwd(), db_rel)
        # Ensure parent directory exists for SQLite
        if db_path:
            parent_dir = os.path.dirname(db_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        if db_path and not os.path.exists(db_path):
            print("Creating new database...")
            init_db()
        else:
            check_and_fix_database()
    
    print("=" * 60)
    print("🎓 Academic Integrity System Started Successfully!")
    print("📍 Access the application at: http://localhost:5000")
    print("👤 Demo Credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("🎨 Features:")
    print("   ✓ Dark/Light mode with auto-detection")
    print("   ✓ Custom background themes")
    print("   ✓ Individual file uploads per student")
    print("   ✓ Advanced plagiarism detection")
    print("   ✓ PDF report generation")
    print("=" * 60)
    
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1', host='0.0.0.0', port=5000)
