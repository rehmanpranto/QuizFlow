from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import json
import csv
import io
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask_mail import Mail, Message
import uuid # Using uuid for more robust submission IDs

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_XnpQSx3Jh0bs@ep-gentle-moon-a1u0xdk9-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Mail Configuration ---
# Configure Flask-Mail with credentials from your .env file
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

# Legacy hardcoded quiz data - now replaced with database-driven approach
# QUIZ_DATA = { ... } - Removed as questions are now stored in database

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # In production, hash this
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with submissions
    submissions = db.relationship('Submission', backref='user', lazy=True)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit = db.Column(db.Integer, default=1200)  # Global time limit in seconds
    time_per_question = db.Column(db.Integer, default=30)  # Time per question in seconds
    is_active = db.Column(db.Boolean, default=True)
    quiz_access_code = db.Column(db.String(20), unique=True, nullable=True)  # Unique student access code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with questions
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='multiple_choice')  # Support for different question types
    option_a = db.Column(db.String(500), nullable=True)  # Nullable for essay questions
    option_b = db.Column(db.String(500), nullable=True)
    option_c = db.Column(db.String(500), nullable=True)
    option_d = db.Column(db.String(500), nullable=True)
    options = db.Column(db.JSON, nullable=True)  # For essay question metadata (instructions, word limits)
    correct_answer = db.Column(db.Text, nullable=False)  # Changed to Text to support essay answers
    order_index = db.Column(db.Integer, default=0)  # For ordering questions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(36), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    detailed_results = db.Column(db.JSON, nullable=True)  # Store as JSON
    access_code = db.Column(db.String(5), nullable=True)  # Store the 5-digit access code
    quiz_start_time = db.Column(db.DateTime, nullable=True)  # When quiz started
    quiz_duration_seconds = db.Column(db.Integer, nullable=True)  # Time taken in seconds


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_type = db.Column(db.String(50), nullable=False, default='free')  # free, basic, pro, enterprise
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled, pending
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=True)
    quizzes_limit = db.Column(db.Integer, default=5)  # Number of quizzes allowed
    quizzes_used = db.Column(db.Integer, default=0)
    students_limit = db.Column(db.Integer, default=50)  # Max students per quiz
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with user
    user = db.relationship('User', backref=db.backref('subscription', uselist=False))


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    payment_method = db.Column(db.String(50), nullable=True)  # stripe, paypal, etc.
    stripe_payment_intent_id = db.Column(db.String(100), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    receipt_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='payments')
    subscription = db.relationship('Subscription', backref='payments')


# Create tables and run migrations on startup
with app.app_context():
    db.create_all()
    # Add quiz_access_code column if it doesn't exist yet
    try:
        with db.engine.connect() as _conn:
            _conn.execute(db.text("ALTER TABLE quizzes ADD COLUMN quiz_access_code VARCHAR(20) UNIQUE"))
            _conn.commit()
    except Exception:
        pass  # Column already exists

# --- Helper function to find submission by ID ---
def find_submission_by_id(submission_id):
    submission = Submission.query.filter_by(submission_id=submission_id).first()
    if submission:
        user = User.query.get(submission.user_id)
        return user.email if user else None, submission
    return None, None

# --- Routes ---
@app.route('/')
def index_page():
    return send_from_directory('.', 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

# --- Admin Routes ---
@app.route('/api/admin/quizzes', methods=['GET'])
def get_all_quizzes():
    """Get all quizzes with their question counts"""
    quizzes = Quiz.query.all()
    quiz_list = []
    
    for quiz in quizzes:
        question_count = Question.query.filter_by(quiz_id=quiz.id).count()
        quiz_list.append({
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "timeLimit": quiz.time_limit,
            "timePerQuestion": quiz.time_per_question,
            "isActive": quiz.is_active,
            "accessCode": quiz.quiz_access_code or "",
            "questionCount": question_count,
            "createdAt": quiz.created_at.isoformat() if quiz.created_at else None
        })
    
    return jsonify({"success": True, "quizzes": quiz_list})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin authentication endpoint"""
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    username = data.get('username', '')
    password = data.get('password', '')
    
    # Admin credentials
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    if username == admin_username and password == admin_password:
        return jsonify({'success': True, 'message': 'Admin login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401

@app.route('/api/admin/quiz/<int:quiz_id>/questions', methods=['GET'])
def get_quiz_questions(quiz_id):
    """Get all questions for a specific quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_index.asc()).all()
    
    question_list = []
    for q in questions:
        question_list.append({
            "id": q.id,
            "questionText": q.question_text,
            "questionType": q.question_type or 'multiple_choice',
            "optionA": q.option_a,
            "optionB": q.option_b,
            "optionC": q.option_c,
            "optionD": q.option_d,
            "correctAnswer": q.correct_answer,
            "orderIndex": q.order_index,
            "options": q.options
        })
    
    return jsonify({
        "success": True, 
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description
        },
        "questions": question_list
    })

@app.route('/api/admin/quiz', methods=['POST'])
def create_quiz():
    """Create a new quiz"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    time_limit = data.get('timeLimit', 1200)
    time_per_question = data.get('timePerQuestion', 30)
    access_code = data.get('accessCode', '').strip() or None
    
    if not title:
        return jsonify({"success": False, "message": "Quiz title is required"}), 400
    
    # Validate access code uniqueness
    if access_code:
        existing = Quiz.query.filter_by(quiz_access_code=access_code).first()
        if existing:
            return jsonify({"success": False, "message": f"Access code '{access_code}' is already in use by another quiz"}), 400
    
    new_quiz = Quiz(
        title=title,
        description=description,
        time_limit=time_limit,
        time_per_question=time_per_question,
        quiz_access_code=access_code,
        is_active=False  # Start as inactive
    )
    
    db.session.add(new_quiz)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Quiz created successfully",
        "quiz": {
            "id": new_quiz.id,
            "title": new_quiz.title,
            "description": new_quiz.description,
            "accessCode": new_quiz.quiz_access_code or ""
        }
    })

@app.route('/api/admin/quiz/<int:quiz_id>/question', methods=['POST'])
def add_question(quiz_id):
    """Add a question to a quiz (supports both multiple choice and essay questions)"""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    question_text = data.get('questionText', '').strip()
    question_type = data.get('question_type', 'multiple_choice')
    
    if not question_text:
        return jsonify({"success": False, "message": "Question text is required"}), 400
    
    # Handle different question types
    if question_type == 'essay':
        # Essay questions
        correct_answer = data.get('correct_answer', '').strip()
        options = data.get('options', {})
        
        if not correct_answer:
            return jsonify({"success": False, "message": "Sample answer is required for essay questions"}), 400
        
        # Get the next order index
        max_order = db.session.query(db.func.max(Question.order_index)).filter_by(quiz_id=quiz_id).scalar() or 0
        
        new_question = Question(
            quiz_id=quiz_id,
            question_text=question_text,
            question_type='essay',
            options=options,  # Store as JSON
            correct_answer=correct_answer,
            order_index=max_order + 1
        )
        
    else:
        # Multiple choice questions
        option_a = data.get('optionA', '').strip()
        option_b = data.get('optionB', '').strip()
        option_c = data.get('optionC', '').strip()
        option_d = data.get('optionD', '').strip()
        correct_answer = data.get('correctAnswer')
        
        if not all([option_a, option_b, option_c, option_d]):
            return jsonify({"success": False, "message": "All options are required for multiple choice questions"}), 400
        
        if correct_answer not in [0, 1, 2, 3]:
            return jsonify({"success": False, "message": "Correct answer must be 0, 1, 2, or 3"}), 400
        
        # Get the next order index
        max_order = db.session.query(db.func.max(Question.order_index)).filter_by(quiz_id=quiz_id).scalar() or 0
        
        new_question = Question(
            quiz_id=quiz_id,
            question_text=question_text,
            question_type='multiple_choice',
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            order_index=max_order + 1
        )
    
    try:
        db.session.add(new_question)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Question added successfully",
            "question": {
                "id": new_question.id,
                "questionText": new_question.question_text,
                "questionType": new_question.question_type,
                "orderIndex": new_question.order_index
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/admin/quiz/<int:quiz_id>/settings', methods=['PUT'])
def update_quiz_settings(quiz_id):
    """Update quiz settings including the access code"""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    if 'title' in data and data['title'].strip():
        quiz.title = data['title'].strip()
    if 'description' in data:
        quiz.description = data['description'].strip()
    if 'timeLimit' in data:
        quiz.time_limit = int(data['timeLimit'])
    if 'timePerQuestion' in data:
        quiz.time_per_question = int(data['timePerQuestion'])

    new_code = data.get('accessCode', '').strip() or None
    if new_code != quiz.quiz_access_code:
        if new_code:
            existing = Quiz.query.filter(Quiz.quiz_access_code == new_code, Quiz.id != quiz_id).first()
            if existing:
                return jsonify({"success": False, "message": f"Access code '{new_code}' is already used by another quiz"}), 400
        quiz.quiz_access_code = new_code

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Quiz settings updated",
        "quiz": {"id": quiz.id, "title": quiz.title, "accessCode": quiz.quiz_access_code or ""}
    })

@app.route('/api/admin/quiz/<int:quiz_id>/activate', methods=['POST'])
def toggle_quiz_status(quiz_id):
    """Activate or deactivate a quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    
    is_active = data.get('isActive', not quiz.is_active)
    
    # If activating this quiz, deactivate all others (only one active quiz at a time)
    if is_active:
        Quiz.query.update({'is_active': False})
    
    quiz.is_active = is_active
    db.session.commit()
    
    status = "activated" if is_active else "deactivated"
    return jsonify({
        "success": True,
        "message": f"Quiz '{quiz.title}' has been {status}",
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "isActive": quiz.is_active
        }
    })

@app.route('/api/admin/students', methods=['GET'])
def get_all_students():
    """Get all registered students with their submission status"""
    users = User.query.all()
    student_list = []
    
    for user in users:
        submission = Submission.query.filter_by(user_id=user.id).first()
        student_list.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "registeredAt": user.created_at.isoformat(),
            "hasSubmitted": submission is not None,
            "submissionDetails": {
                "score": submission.score,
                "percentage": submission.percentage,
                "submittedAt": submission.submitted_at.isoformat()
            } if submission else None
        })
    
    return jsonify({"success": True, "students": student_list})

@app.route('/api/admin/results/download', methods=['GET'])
def download_results():
    """Download all quiz submission results as a CSV file"""
    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'Submission ID', 'Student Name', 'Email', 'Access Code',
        'Score', 'Total Questions', 'Percentage (%)', 'Feedback',
        'Duration (seconds)', 'Submitted At'
    ])

    for sub in submissions:
        user = User.query.get(sub.user_id)
        writer.writerow([
            sub.submission_id,
            user.name if user else 'N/A',
            user.email if user else 'N/A',
            sub.access_code or 'N/A',
            sub.score,
            sub.total_questions,
            f"{sub.percentage:.2f}",
            sub.feedback or '',
            sub.quiz_duration_seconds or '',
            sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if sub.submitted_at else ''
        ])

    output.seek(0)
    filename = f"quizflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


    """Send custom email to students"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    recipient_emails = data.get('recipients', [])  # List of email addresses
    subject = data.get('subject', '').strip()
    message_body = data.get('message', '').strip()
    send_to_all = data.get('sendToAll', False)
    
    if not subject or not message_body:
        return jsonify({"success": False, "message": "Subject and message are required"}), 400
    
    # Get recipients
    if send_to_all:
        users = User.query.all()
        recipients = [user.email for user in users]
    else:
        recipients = recipient_emails
    
    if not recipients:
        return jsonify({"success": False, "message": "No recipients specified"}), 400
    
    # Send emails
    sent_count = 0
    failed_count = 0
    
    for email in recipients:
        try:
            msg = Message(
                subject=f"📢 {subject}",
                recipients=[email],
                body=f"""
{message_body}

---
This message was sent via QuizFlow Admin Panel
{datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                """.strip()
            )
            mail.send(msg)
            sent_count += 1
            print(f"✅ Email sent to: {email}")
        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to send email to {email}: {e}")
    
    return jsonify({
        "success": True,
        "message": f"Email sent to {sent_count} recipients. {failed_count} failed.",
        "sentCount": sent_count,
        "failedCount": failed_count
    })

@app.route('/api/validate-code', methods=['POST'])
def validate_code():
    """Endpoint to validate if a code is valid without logging in"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    code = data.get('code')
    if not code:
        return jsonify({"success": False, "message": "Code is required"}), 400
    
    if not code.isdigit() or len(code) != 5:
        return jsonify({"success": False, "message": "Code must be exactly 5 digits"}), 400
    
    valid_codes = os.getenv('VALID_LOGIN_CODES', '12345,67890,11111,22222,33333').split(',')
    
    if code in valid_codes:
        return jsonify({"success": True, "message": "Valid code", "isValid": True}), 200
    else:
        return jsonify({"success": False, "message": "Invalid code", "isValid": False}), 200



@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    login_code = data.get('code')
    student_name = data.get('name', '').strip()
    student_email = data.get('email', '').strip()

    if not login_code:
        return jsonify({"success": False, "message": "Login code is required"}), 400
    
    if not student_name:
        return jsonify({"success": False, "message": "Student name is required"}), 400
    
    if not student_email:
        return jsonify({"success": False, "message": "Email address is required"}), 400
    
    # Validate email format
    import re
    email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_pattern, student_email):
        return jsonify({"success": False, "message": "Please enter a valid email address"}), 400

    # Validate the code format
    if not login_code.isdigit() or len(login_code) < 4:
        return jsonify({"success": False, "message": "Invalid code format. Please enter a valid access code."}), 400

    # First: check if code matches a specific quiz's access code
    quiz_by_code = Quiz.query.filter_by(quiz_access_code=login_code).first()
    
    # Fallback: check global VALID_LOGIN_CODES
    if not quiz_by_code:
        valid_codes = os.getenv('VALID_LOGIN_CODES', '12345,67890,11111,22222,33333').split(',')
        if login_code not in valid_codes:
            return jsonify({"success": False, "message": "Invalid access code. Please check your code and try again."}), 401

    # Check if this student has already taken the quiz with this email and code combination
    existing_user = User.query.filter_by(email=student_email).first()
    
    if existing_user:
        # Check if user has already submitted quiz
        submission = Submission.query.filter_by(user_id=existing_user.id).first()
        if submission:
            # Get quiz title — prefer the quiz matched by access code
            quiz = quiz_by_code or Quiz.query.filter_by(is_active=True).first()
            quiz_title = quiz.title if quiz else "the quiz"
            
            return jsonify({
                "success": True,
                "quizAlreadyTaken": True,
                "message": f"You have already completed '{quiz_title}' with this code.",
                "email": student_email,
                "userId": student_email,
                "studentName": student_name,
                "pastResults": {
                    "submissionId": submission.submission_id,
                    "score": submission.score,
                    "totalQuestions": submission.total_questions,
                    "percentage": submission.percentage,
                    "feedback": submission.feedback,
                    "detailedResults": submission.detailed_results
                }
            }), 200
        else:
            return jsonify({
                "success": True, 
                "message": "Login successful. You can start the quiz.", 
                "email": student_email,
                "userId": student_email,
                "studentName": student_name
            }), 200
    else:
        # Create new user entry for this student
        new_user = User(
            name=student_name,
            email=student_email,
            password=login_code  # Store the code as password for reference
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Send welcome email to new student
        send_welcome_emails = os.getenv('SEND_STUDENT_EMAILS', 'true').lower() in ['true', '1', 'yes']
        if send_welcome_emails:
            try:
                # Get quiz info for welcome email
                active_quiz = Quiz.query.filter_by(is_active=True).first()
                quiz_info = f"You're about to take: {active_quiz.title}" if active_quiz else "Get ready for your quiz!"
                
                welcome_subject = f"🎯 Welcome to QuizFlow - Ready to Start?"
                welcome_body = f"""
🎉 Hello {student_name}!

Welcome to QuizFlow! You have successfully logged in and are ready to begin your quiz.

📋 QUIZ INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quiz_info}
🔐 Your access code: {login_code}
📧 Email: {student_email}
📅 Login time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

📝 INSTRUCTIONS:
• Make sure you have a stable internet connection
• Take your time to read each question carefully  
• You can only submit the quiz once
• Your results will be emailed to you upon completion

Good luck! We're rooting for you! 🚀

Best regards,
The QuizFlow Team
                """.strip()
                
                welcome_msg = Message(
                    subject=welcome_subject,
                    recipients=[student_email],
                    body=welcome_body
                )
                mail.send(welcome_msg)
                print(f"✅ Successfully sent welcome email to: {student_email}")
                
            except Exception as e:
                print(f"❌ FAILED to send welcome email: {e}")
        
        return jsonify({
            "success": True, 
            "message": "Login successful. You can start the quiz.", 
            "email": student_email,
            "userId": student_email,
            "studentName": student_name
        }), 200

@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    # Look up quiz by access code first, then fall back to active quiz
    code = request.args.get('code', '').strip()
    if code:
        quiz = Quiz.query.filter_by(quiz_access_code=code).first()
        if not quiz:
            return jsonify({"success": False, "message": "No quiz found for this access code"}), 404
    else:
        quiz = Quiz.query.filter_by(is_active=True).first()
        if not quiz:
            return jsonify({"success": False, "message": "No active quiz found"}), 404
    
    # Get questions for this quiz, ordered by order_index
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index.asc()).all()
    
    if not questions:
        return jsonify({
            "success": False,
            "message": "No questions found for this quiz"
        }), 404
    
    # Format questions for frontend
    formatted_questions = []
    for q in questions:
        formatted_questions.append({
            "id": q.id,
            "question": q.question_text,
            "options": [q.option_a, q.option_b, q.option_c, q.option_d]
        })
    
    return jsonify({
        "success": True,
        "title": quiz.title,
        "timePerQuestion": quiz.time_per_question,
        "timeLimit": quiz.time_limit,
        "questions": formatted_questions
    })

@app.route('/api/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    # Handle both old format (email) and new format (name+code)
    user_email = data.get('email')
    student_name = data.get('name', '').strip()
    login_code = data.get('code')
    user_answers_indices = data.get('answers', [])
    quiz_start_time_str = data.get('quizStartTime')
    quiz_duration_seconds = data.get('quizDurationSeconds')

    if not isinstance(user_answers_indices, list):
        return jsonify({"success": False, "message": "A valid answers list is required."}), 400

    # Create user identifier for new format
    if student_name and login_code:
        user_identifier = f"{login_code}_{student_name.lower().replace(' ', '_')}"
    elif user_email:
        user_identifier = user_email
    else:
        return jsonify({"success": False, "message": "Either email or name+code are required."}), 400

    # Parse quiz start time if provided
    quiz_start_time = None
    if quiz_start_time_str:
        try:
            quiz_start_time = datetime.fromisoformat(quiz_start_time_str.replace('Z', '+00:00'))
        except ValueError:
            quiz_start_time = None

    # Find user in database
    user = User.query.filter_by(email=user_identifier).first()
    if not user:
        return jsonify({"success": False, "message": "User not found. Please login first."}), 401
    
    # Check if user has already submitted
    existing_submission = Submission.query.filter_by(user_id=user.id).first()
    if existing_submission:
        return jsonify({"success": False, "message": "This quiz has already been submitted by you."}), 403

    # Get the active quiz and its questions
    quiz = Quiz.query.filter_by(is_active=True).first()
    if not quiz:
        return jsonify({"success": False, "message": "No active quiz found"}), 404
    
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index.asc()).all()
    if not questions:
        return jsonify({"success": False, "message": "No questions found for this quiz"}), 404

    score = 0
    total_questions = len(questions)
    detailed_results = []

    for i, question in enumerate(questions):
        correct_answer_index = question.correct_answer
        user_selected_index = user_answers_indices[i] if i < len(user_answers_indices) else None
        
        is_correct = (user_selected_index is not None and int(user_selected_index) == correct_answer_index)
        if is_correct:
            score += 1

        # Get the option texts
        options = [question.option_a, question.option_b, question.option_c, question.option_d]
        
        detailed_results.append({
            "id": question.id,
            "question_text": question.question_text,
            "user_selected_answer_text": options[user_selected_index] if user_selected_index is not None else "Not Answered",
            "correct_answer_text": options[correct_answer_index],
            "is_correct": is_correct
        })

    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    name = user.name.split(' ')[0]

    if percentage == 100: feedback_text = f"Perfect score, {name}! You're a demand and supply expert!"
    elif percentage >= 80: feedback_text = f"Excellent work, {name}!"
    elif percentage >= 60: feedback_text = f"Good job, {name}! Solid understanding."
    else: feedback_text = f"Keep practicing, {name}. You'll get there!"

    submission_id = str(uuid.uuid4())
    
    # Save submission to database
    new_submission = Submission(
        submission_id=submission_id,
        user_id=user.id,
        score=score,
        total_questions=total_questions,
        percentage=round(percentage, 2),
        feedback=feedback_text,
        detailed_results=detailed_results,
        access_code=login_code if login_code else None,
        quiz_start_time=quiz_start_time,
        quiz_duration_seconds=quiz_duration_seconds
    )
    db.session.add(new_submission)
    db.session.commit()
    
    print(f"Quiz submitted by: {user_email}, Score: {score}/{total_questions}")

    # --- Send Email Notifications ---
    
    # 1. Send email to student with their results (if enabled)
    send_student_emails = os.getenv('SEND_STUDENT_EMAILS', 'true').lower() in ['true', '1', 'yes']
    
    if send_student_emails:
        try:
            student_subject = f"🎯 Quiz Results: {quiz.title}"
            
            # Create a nicely formatted email with emoji indicators
            grade_emoji = "🏆" if percentage >= 90 else "🥉" if percentage >= 80 else "📚" if percentage >= 60 else "💪"
            
            # Create detailed results for email
            detailed_email_results = []
            for i, result in enumerate(detailed_results, 1):
                status_emoji = "✅" if result['is_correct'] else "❌"
                detailed_email_results.append(
                    f"{i}. {result['question_text']}\n"
                    f"   Your answer: {result['user_selected_answer_text']}\n"
                    f"   Correct answer: {result['correct_answer_text']}\n"
                    f"   {status_emoji} {status_emoji if result['is_correct'] else 'Incorrect'}\n"
                )
            
            # Format duration nicely
            duration_text = ""
            if quiz_duration_seconds:
                minutes = quiz_duration_seconds // 60
                seconds = quiz_duration_seconds % 60
                duration_text = f"⏱️ Time taken: {minutes}:{seconds:02d} minutes\n"
            
            student_body = f"""
{grade_emoji} Dear {user.name},

Congratulations on completing the "{quiz.title}"!

📊 YOUR RESULTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Score: {score}/{total_questions} ({percentage:.1f}%)
💬 {feedback_text}
{duration_text}📅 Completed: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

📋 DETAILED BREAKDOWN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(detailed_email_results)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thank you for participating! Keep up the great work! 🚀

Best regards,
The QuizFlow Team
            """.strip()
            
            student_msg = Message(
                subject=student_subject, 
                recipients=[user.email], 
                body=student_body
            )
            mail.send(student_msg)
            print(f"✅ Successfully sent results email to student: {user.email}")
            
        except Exception as e:
            print(f"❌ FAILED to send results email to student: {e}")
    
    # 2. Send notification to admin
    admin_email = os.getenv('ADMIN_EMAIL_RECIPIENT')
    if admin_email:
        try:
            admin_subject = f"Quiz Submission: {user.email} on '{quiz.title}'"
            admin_body = f"""
New quiz submission received:

Student: {user.name} ({user.email})
Quiz: {quiz.title}
Score: {score}/{total_questions} ({percentage:.2f}%)
Access Code: {login_code}
Duration: {quiz_duration_seconds // 60}:{quiz_duration_seconds % 60:02d} minutes
Submitted: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Feedback given: {feedback_text}
            """.strip()
            
            admin_msg = Message(
                subject=admin_subject, 
                recipients=[admin_email], 
                body=admin_body, 
                reply_to=user.email
            )
            mail.send(admin_msg)
            print(f"Successfully sent notification email to admin: {admin_email}")
            
        except Exception as e:
            print(f"!!! FAILED to send notification email to admin: {e}")

    return jsonify({
        "success": True,
        "submissionId": submission_id,
        "score": score,
        "totalQuestions": total_questions,
        "percentage": round(percentage, 2),
        "feedback": feedback_text,
        "detailedResults": detailed_results,
        "accessCode": login_code,
        "quizDurationSeconds": quiz_duration_seconds,
        "quizStartTime": quiz_start_time.isoformat() if quiz_start_time else None
    }), 200

@app.route('/api/user/submissions', methods=['GET'])
def get_user_submissions():
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"success": False, "message": "User email parameter is required."}), 400

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"success": False, "message": "User account not found."}), 404

    # Get the active quiz for title reference
    quiz = Quiz.query.filter_by(is_active=True).first()
    quiz_title = quiz.title if quiz else "Quiz"

    submissions_list = []
    submissions = Submission.query.filter_by(user_id=user.id).all()
    for sub in submissions:
        submissions_list.append({
            "submissionId": sub.submission_id,
            "quizTitle": quiz_title,
            "score": sub.score,
            "totalQuestionsInQuiz": sub.total_questions,
            "percentage": sub.percentage,
            "submittedAt": sub.submitted_at.isoformat()
        })
    
    return jsonify({"success": True, "submissions": submissions_list})

@app.route('/api/submission/<submission_id_str>/details', methods=['GET'])
def get_submission_details(submission_id_str):
    user_email, submission = find_submission_by_id(submission_id_str)

    if not submission:
        return jsonify({"success": False, "message": "Submission not found."}), 404

    # Get the active quiz for title reference
    quiz = Quiz.query.filter_by(is_active=True).first()
    quiz_title = quiz.title if quiz else "Quiz"

    summary_response = {
        "submissionId": submission.submission_id,
        "quizTitle": quiz_title,
        "score": submission.score,
        "totalQuestionsInQuiz": submission.total_questions,
        "percentage": submission.percentage,
        "feedback": submission.feedback,
        "submittedAt": submission.submitted_at.isoformat(),
        "userEmail": user_email
    }
    
    return jsonify({
        "success": True, 
        "summary": summary_response, 
        "details": submission.detailed_results
    })

@app.route('/api/admin/quiz/<int:quiz_id>', methods=['DELETE'])  
def delete_quiz(quiz_id):
    """Delete a quiz and all its questions"""
    try:
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        quiz_title = quiz.title
        
        # Delete all questions associated with the quiz (CASCADE should handle this)
        Question.query.filter_by(quiz_id=quiz_id).delete()
        
        # Delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Quiz '{quiz_title}' and all its questions deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/question/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Delete a specific question"""
    try:
        question = Question.query.get(question_id)
        if not question:
            return jsonify({"success": False, "message": "Question not found"}), 404
        
        db.session.delete(question)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Question deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/question/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """Update a specific question"""
    try:
        question = Question.query.get(question_id)
        if not question:
            return jsonify({"success": False, "message": "Question not found"}), 404
        
        data = request.get_json()
        question_text = data.get('questionText', '').strip()
        question_type = data.get('question_type', 'multiple_choice')
        
        if not question_text:
            return jsonify({"success": False, "message": "Question text is required"}), 400
        
        # Update basic fields
        question.question_text = question_text
        question.question_type = question_type
        
        if question_type == 'essay':
            # Essay question updates
            correct_answer = data.get('correct_answer', '').strip()
            if not correct_answer:
                return jsonify({"success": False, "message": "Sample answer is required for essay questions"}), 400
            
            options = data.get('options', {})
            question.correct_answer = correct_answer
            question.options = options
            
            # Clear multiple choice fields for essay questions
            question.option_a = None
            question.option_b = None
            question.option_c = None
            question.option_d = None
            
        else:
            # Multiple choice question updates
            option_a = data.get('optionA', '').strip()
            option_b = data.get('optionB', '').strip()
            option_c = data.get('optionC', '').strip()
            option_d = data.get('optionD', '').strip()
            correct_answer = data.get('correctAnswer')
            
            if not all([option_a, option_b, option_c, option_d]):
                return jsonify({"success": False, "message": "All options are required for multiple choice questions"}), 400
            
            if correct_answer not in [0, 1, 2, 3]:
                return jsonify({"success": False, "message": "Correct answer must be 0, 1, 2, or 3"}), 400
            
            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d
            question.correct_answer = correct_answer
            question.options = None  # Clear options for multiple choice
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Question updated successfully",
            "question": {
                "id": question.id,
                "questionText": question.question_text,
                "questionType": question.question_type
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ==================== Subscription & Payment API Endpoints ====================

@app.route('/api/subscription', methods=['GET'])
def get_subscription():
    """Get current user's subscription information"""
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400

        subscription = Subscription.query.filter_by(user_id=int(user_id)).first()
        
        if not subscription:
            # Create default free subscription
            subscription = Subscription(
                user_id=int(user_id),
                plan_type='free',
                status='active',
                quizzes_limit=5,
                quizzes_used=0,
                students_limit=50
            )
            db.session.add(subscription)
            db.session.commit()

        return jsonify({
            "success": True,
            "subscription": {
                "id": subscription.id,
                "plan_type": subscription.plan_type,
                "status": subscription.status,
                "quizzes_limit": subscription.quizzes_limit,
                "quizzes_used": subscription.quizzes_used,
                "quizzes_remaining": subscription.quizzes_limit - subscription.quizzes_used,
                "students_limit": subscription.students_limit,
                "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
                "expiry_date": subscription.expiry_date.isoformat() if subscription.expiry_date else None,
                "created_at": subscription.created_at.isoformat() if subscription.created_at else None
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/subscription/upgrade', methods=['POST'])
def upgrade_subscription():
    """Upgrade user's subscription plan"""
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400

        data = request.get_json()
        plan_type = data.get('plan_type', 'basic')
        
        # Define plan limits
        plan_limits = {
            'free': {'quizzes_limit': 5, 'students_limit': 50, 'price': 0},
            'basic': {'quizzes_limit': 20, 'students_limit': 100, 'price': 9.99},
            'pro': {'quizzes_limit': 100, 'students_limit': 500, 'price': 29.99},
            'enterprise': {'quizzes_limit': -1, 'students_limit': -1, 'price': 99.99}  # -1 means unlimited
        }
        
        if plan_type not in plan_limits:
            return jsonify({"success": False, "message": "Invalid plan type"}), 400

        subscription = Subscription.query.filter_by(user_id=int(user_id)).first()
        
        if not subscription:
            subscription = Subscription(user_id=int(user_id))
            db.session.add(subscription)
        
        limits = plan_limits[plan_type]
        subscription.plan_type = plan_type
        subscription.quizzes_limit = limits['quizzes_limit']
        subscription.students_limit = limits['students_limit']
        subscription.status = 'active'
        
        # Set expiry based on plan (30 days from now for paid plans)
        if plan_type != 'free':
            from datetime import timedelta
            subscription.expiry_date = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully upgraded to {plan_type} plan",
            "subscription": {
                "plan_type": subscription.plan_type,
                "quizzes_limit": subscription.quizzes_limit,
                "students_limit": subscription.students_limit,
                "expiry_date": subscription.expiry_date.isoformat() if subscription.expiry_date else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """Create a new payment record"""
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400

        data = request.get_json()
        amount = data.get('amount', 0)
        plan_type = data.get('plan_type', 'basic')
        payment_method = data.get('payment_method', 'stripe')
        stripe_payment_intent_id = data.get('stripe_payment_intent_id')

        if amount <= 0:
            return jsonify({"success": False, "message": "Invalid amount"}), 400

        payment = Payment(
            user_id=int(user_id),
            amount=amount,
            currency='USD',
            status='completed',
            payment_method=payment_method,
            stripe_payment_intent_id=stripe_payment_intent_id,
            description=f"Subscription upgrade to {plan_type} plan"
        )
        db.session.add(payment)
        db.session.commit()

        # Update subscription
        upgrade_subscription()

        return jsonify({
            "success": True,
            "message": "Payment processed successfully",
            "payment": {
                "id": payment.id,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "created_at": payment.created_at.isoformat() if payment.created_at else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/payments', methods=['GET'])
def get_payments():
    """Get payment history for admin or user"""
    try:
        user_id = request.headers.get('X-User-Id')
        is_admin = request.headers.get('X-Is-Admin', 'false').lower() == 'true'
        
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400

        if is_admin:
            # Admin can see all payments
            payments = Payment.query.order_by(Payment.created_at.desc()).limit(100).all()
        else:
            # User can only see their own payments
            payments = Payment.query.filter_by(user_id=int(user_id)).order_by(Payment.created_at.desc()).limit(50).all()

        return jsonify({
            "success": True,
            "payments": [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "amount": p.amount,
                    "currency": p.currency,
                    "status": p.status,
                    "payment_method": p.payment_method,
                    "description": p.description,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in payments
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/admin/subscriptions', methods=['GET'])
def get_all_subscriptions():
    """Get all subscriptions (admin only)"""
    try:
        subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).limit(100).all()
        
        return jsonify({
            "success": True,
            "subscriptions": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "plan_type": s.plan_type,
                    "status": s.status,
                    "quizzes_limit": s.quizzes_limit,
                    "quizzes_used": s.quizzes_used,
                    "students_limit": s.students_limit,
                    "start_date": s.start_date.isoformat() if s.start_date else None,
                    "expiry_date": s.expiry_date.isoformat() if s.expiry_date else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in subscriptions
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/quiz/create', methods=['POST'])
def create_quiz_endpoint():
    """Create a new quiz (checks subscription limits)"""
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400

        # Check subscription limits
        subscription = Subscription.query.filter_by(user_id=int(user_id)).first()
        
        if subscription and subscription.quizzes_limit > 0:
            if subscription.quizzes_used >= subscription.quizzes_limit:
                return jsonify({
                    "success": False,
                    "message": "Quiz limit reached. Please upgrade your subscription to create more quizzes."
                }), 403

        data = request.get_json()
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        time_limit = data.get('time_limit', 1200)
        quiz_access_code = data.get('quiz_access_code')

        if not title:
            return jsonify({"success": False, "message": "Quiz title is required"}), 400

        quiz = Quiz(
            title=title,
            description=description,
            time_limit=time_limit,
            quiz_access_code=quiz_access_code,
            is_active=True
        )
        db.session.add(quiz)
        db.session.commit()

        # Update subscription quiz count
        if subscription and subscription.quizzes_limit > 0:
            subscription.quizzes_used += 1
            db.session.commit()

        return jsonify({
            "success": True,
            "message": "Quiz created successfully",
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "quiz_access_code": quiz.quiz_access_code
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/admin/ai/generate-questions', methods=['POST'])
def generate_ai_questions():
    """Generate questions using OpenAI API"""
    try:
        import openai
        from openai import OpenAI
        
        data = request.get_json()
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', 'intermediate')
        question_type = data.get('questionType', 'multiple_choice')
        num_questions = data.get('numQuestions', 5)
        context = data.get('context', '').strip()
        
        if not topic:
            return jsonify({"success": False, "message": "Topic is required"}), 400
        
        # Get OpenAI API key from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            return jsonify({"success": False, "message": "OpenAI API key not configured"}), 500
        
        # Initialize OpenAI client
        client = OpenAI(
            api_key=api_key,
            organization=os.getenv('OPENAI_ORGANIZATION')
        )
        
        # Create the prompt based on question type
        if question_type == 'multiple_choice':
            prompt = f"""Create {num_questions} multiple choice questions about {topic} at {difficulty} level.
{f'Additional context: {context}' if context else ''}

For each question, provide:
1. Question text
2. Four options (A, B, C, D)  
3. Correct answer (A, B, C, or D)
4. Brief explanation

Format as JSON array with objects containing: questionText, optionA, optionB, optionC, optionD, correctAnswer (0-3), explanation"""

        elif question_type == 'essay':
            prompt = f"""Create {num_questions} essay questions about {topic} at {difficulty} level.
{f'Additional context: {context}' if context else ''}

For each question, provide:
1. Question text
2. Sample answer/key points
3. Instructions for students
4. Suggested word count

Format as JSON array with objects containing: questionText, sampleAnswer, instructions, maxWords"""

        else:  # mixed
            mc_count = num_questions // 2
            essay_count = num_questions - mc_count
            prompt = f"""Create {mc_count} multiple choice and {essay_count} essay questions about {topic} at {difficulty} level.
{f'Additional context: {context}' if context else ''}

For multiple choice questions, provide: questionText, optionA, optionB, optionC, optionD, correctAnswer (0-3), explanation, type: "multiple_choice"
For essay questions, provide: questionText, sampleAnswer, instructions, maxWords, type: "essay"

Format as JSON array."""

        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert educator who creates high-quality quiz questions. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Parse the response
        generated_content = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure it's valid JSON
        if generated_content.startswith('```json'):
            generated_content = generated_content[7:]
        if generated_content.endswith('```'):
            generated_content = generated_content[:-3]
        
        generated_questions = json.loads(generated_content)
        
        return jsonify({
            "success": True,
            "questions": generated_questions,
            "message": f"Generated {len(generated_questions)} questions successfully"
        })
        
    except ImportError:
        return jsonify({"success": False, "message": "OpenAI library not installed. Run: pip install openai"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"success": False, "message": f"Failed to parse AI response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"AI generation failed: {str(e)}"}), 500

def migrate_database():
    """Add new columns to existing tables if they don't exist"""
    try:
        # Check if new columns exist and add them if missing
        with db.engine.connect() as conn:
            # Add access_code column if it doesn't exist
            try:
                conn.execute(db.text("ALTER TABLE submissions ADD COLUMN access_code VARCHAR(5)"))
                print("Added access_code column to submissions table")
            except Exception:
                pass  # Column already exists
            
            # Add quiz_start_time column if it doesn't exist  
            try:
                conn.execute(db.text("ALTER TABLE submissions ADD COLUMN quiz_start_time TIMESTAMP"))
                print("Added quiz_start_time column to submissions table")
            except Exception:
                pass  # Column already exists
                
            # Add quiz_duration_seconds column if it doesn't exist
            try:
                conn.execute(db.text("ALTER TABLE submissions ADD COLUMN quiz_duration_seconds INTEGER"))
                print("Added quiz_duration_seconds column to submissions table")
            except Exception:
                pass  # Column already exists

            # Add quiz_access_code column to quizzes if it doesn't exist
            try:
                conn.execute(db.text("ALTER TABLE quizzes ADD COLUMN quiz_access_code VARCHAR(20) UNIQUE"))
                print("Added quiz_access_code column to quizzes table")
            except Exception:
                pass  # Column already exists
            
            conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")

def populate_sample_quiz():
    """Populate database with sample quiz data if no quiz exists"""
    existing_quiz = Quiz.query.first()
    if existing_quiz:
        print("Quiz data already exists, skipping sample data creation")
        return
    
    # Check if we should skip sample data creation
    skip_sample = os.getenv('SKIP_SAMPLE_DATA', 'false').lower() in ['true', '1', 'yes']
    if skip_sample:
        print("Skipping sample data creation (SKIP_SAMPLE_DATA=true)")
        return
    
    print("Creating sample quiz data...")
    
    # Create sample quiz
    sample_quiz = Quiz(
        title="Demand and Supply Quiz",
        description="Test your knowledge of basic economic principles of demand and supply",
        time_limit=1200,  # 20 minutes
        time_per_question=30,  # 30 seconds per question
        is_active=True
    )
    db.session.add(sample_quiz)
    db.session.flush()  # Get the quiz ID
    
    # Sample questions data
    sample_questions = [
        {
            "question_text": "What does the Law of Demand state, ceteris paribus?",
            "option_a": "As price increases, quantity demanded increases",
            "option_b": "As price increases, quantity demanded decreases",
            "option_c": "As supply increases, demand increases",
            "option_d": "As income increases, demand always increases",
            "correct_answer": 1
        },
        {
            "question_text": "Which of the following can shift the demand curve to the right?",
            "option_a": "A decrease in consumer income (for normal goods)",
            "option_b": "A fall in the price of a complement",
            "option_c": "A fall in the price of the good itself",
            "option_d": "An increase in input prices",
            "correct_answer": 1
        },
        {
            "question_text": "The substitution effect means that:",
            "option_a": "Consumers substitute inferior goods with luxury goods",
            "option_b": "A good becomes more desirable as it becomes more expensive",
            "option_c": "Consumers switch to a good when its price falls relative to substitutes",
            "option_d": "Consumers always prefer imported goods",
            "correct_answer": 2
        },
        {
            "question_text": "Which of the following is not a determinant of supply?",
            "option_a": "Input prices",
            "option_b": "Technology",
            "option_c": "Consumer tastes",
            "option_d": "Government subsidies",
            "correct_answer": 2
        },
        {
            "question_text": "A rightward shift in the supply curve results in:",
            "option_a": "Higher prices and lower quantity",
            "option_b": "Lower prices and higher quantity",
            "option_c": "No change in equilibrium",
            "option_d": "Lower prices and lower quantity",
            "correct_answer": 1
        },
        {
            "question_text": "What causes movement along the demand curve?",
            "option_a": "Change in price of substitute goods",
            "option_b": "Change in consumer income",
            "option_c": "Change in the price of the good itself",
            "option_d": "Change in consumer expectations",
            "correct_answer": 2
        },
        {
            "question_text": "Market equilibrium occurs when:",
            "option_a": "Quantity supplied is greater than quantity demanded",
            "option_b": "Demand equals supply",
            "option_c": "Supply increases rapidly",
            "option_d": "Demand is falling while price is rising",
            "correct_answer": 1
        },
        {
            "question_text": "A shortage occurs when:",
            "option_a": "Quantity supplied exceeds quantity demanded",
            "option_b": "Price is above equilibrium",
            "option_c": "Price is below equilibrium",
            "option_d": "Demand curve shifts left",
            "correct_answer": 2
        },
        {
            "question_text": "The Law of Supply states that:",
            "option_a": "As price rises, supply decreases",
            "option_b": "As price rises, supply increases",
            "option_c": "Supply is not affected by price",
            "option_d": "Supply only increases when demand increases",
            "correct_answer": 1
        },
        {
            "question_text": "Which factor will most likely cause a leftward shift in the supply curve?",
            "option_a": "Technological advancement",
            "option_b": "Fall in input costs",
            "option_c": "Increase in taxes",
            "option_d": "Increase in number of sellers",
            "correct_answer": 2
        }
    ]
    
    # Add questions to database
    for i, q_data in enumerate(sample_questions):
        question = Question(
            quiz_id=sample_quiz.id,
            question_text=q_data["question_text"],
            option_a=q_data["option_a"],
            option_b=q_data["option_b"],
            option_c=q_data["option_c"],
            option_d=q_data["option_d"],
            correct_answer=q_data["correct_answer"],
            order_index=i + 1
        )
        db.session.add(question)
    
    db.session.commit()
    print(f"Created sample quiz '{sample_quiz.title}' with {len(sample_questions)} questions")

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Quizflow application on port {port}...")
    with app.app_context():
        db.create_all()
        migrate_database()
        populate_sample_quiz()
        print("Database tables created and migrated successfully.")
    app.run(debug=True, port=port)
