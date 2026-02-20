"""
QuizFlow Subscription Integration
==================================
This module provides integration code to add subscription enforcement
to the existing QuizFlow app.py file.

INSTRUCTIONS:
1. Add the imports marked with [ADD] to app.py
2. Add the configuration marked with [ADD] to app.py
3. Register the blueprint marked with [ADD] to app.py
4. Update the create_quiz function with the enforcement check
"""

# ============================================================================
# STEP 1: ADD THESE IMPORTS TO app.py
# ============================================================================
"""
# Add these imports at the top of app.py with other imports:

from models.subscription_models import (  # [ADD]
    db, SubscriptionPlan, Payment, UserSubscription, 
    AdminAuditLog, RateLimitLog, User as SubscriptionUser
)
from routes.subscription_routes import subscription_bp  # [ADD]
from utils.email_utils import (  # [ADD]
    send_email, send_account_creation_email,
    send_payment_confirmation_email, generate_secure_password,
    generate_username_from_email, validate_email, get_mail_config
)
from datetime import datetime, timezone, timedelta  # [ADD] if not already imported
"""


# ============================================================================
# STEP 2: ADD MAIL CONFIGURATION TO app.py
# ============================================================================
"""
# After the existing mail configuration in app.py, add:

# [ADD] Merge with existing mail config or replace with:
app.config.update(get_mail_config())
mail = Mail(app)  # Reinitialize with updated config
"""


# ============================================================================
# STEP 3: INITIALIZE DATABASE AND REGISTER BLUEPRINT
# ============================================================================
"""
# After creating the Flask app and before running, add:

# [ADD] Initialize subscription models
from models.subscription_models import init_subscription_models
init_subscription_models(app)

# [ADD] Register subscription blueprint
app.register_blueprint(subscription_bp)
"""


# ============================================================================
# STEP 4: UPDATE ADMIN AUTHENTICATION TO SUPPORT TEACHERS
# ============================================================================
"""
# Update the admin_login route in app.py to support teacher login:

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    \"\"\"Admin/Teacher authentication endpoint\"\"\"
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    username = data.get('username', '')
    password = data.get('password', '')

    # [ADD] Check teacher/admin users in database first
    user = SubscriptionUser.query.filter(
        (SubscriptionUser.username == username) | (SubscriptionUser.email == username)
    ).first()
    
    if user and user.check_password(password):
        if user.role in ['teacher', 'admin']:
            # [ADD] Store user info in session
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['is_admin'] = (user.role == 'admin')
            session['admin_username'] = user.username or user.email
            
            return jsonify({
                'success': True, 
                'message': f'Login successful as {user.role}',
                'role': user.role,
                'email': user.email
            })
    
    # [KEEP] Fallback to environment variable admin credentials
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

    if username == admin_username and password == admin_password:
        session['user_id'] = 1
        session['user_email'] = admin_username
        session['is_admin'] = True
        session['admin_username'] = admin_username
        return jsonify({'success': True, 'message': 'Admin login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
"""


# ============================================================================
# STEP 5: ADD QUIZ CREATION LIMIT ENFORCEMENT
# ============================================================================
"""
# Update the create_quiz route in app.py to check subscription limits:

@app.route('/api/admin/quiz', methods=['POST'])
def create_quiz():
    \"\"\"Create a new quiz with subscription limit enforcement\"\"\"
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    # [ADD] Check if user is authenticated
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "Authentication required. Please login as a teacher."
        }), 401

    # [ADD] Get user and check subscription
    user = SubscriptionUser.query.get(user_id)
    
    if not user:
        # Try to find by email (for backward compatibility)
        user = SubscriptionUser.query.filter_by(email=user_email).first()
    
    if not user or user.role != 'teacher':
        return jsonify({
            "success": False, 
            "message": "Only teachers can create quizzes. Please subscribe to create quizzes."
        }), 403
    
    # [ADD] Check subscription status
    subscription = UserSubscription.get_active_subscription(user_id)
    
    if not subscription:
        return jsonify({
            "success": False, 
            "message": "No active subscription found. Please subscribe to create quizzes.",
            "redirect": "/pricing.html"
        }), 403
    
    if not subscription.can_create_quiz():
        if subscription.expiry_date < datetime.now(timezone.utc):
            return jsonify({
                "success": False, 
                "message": "Your subscription has expired. Please renew to create more quizzes.",
                "redirect": "/pricing.html"
            }), 403
        
        if subscription.quizzes_used >= subscription.quiz_limit:
            return jsonify({
                "success": False, 
                "message": f"You have reached your quiz limit ({subscription.quiz_limit} quizzes). Please upgrade your plan to create more quizzes.",
                "redirect": "/pricing.html"
            }), 403

    # [KEEP] Existing quiz creation logic
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
        is_active=False
    )

    db.session.add(new_quiz)
    db.session.commit()

    # [ADD] Increment quiz usage counter
    subscription.increment_quiz_usage()

    return jsonify({
        "success": True,
        "message": "Quiz created successfully",
        "quiz": {
            "id": new_quiz.id,
            "title": new_quiz.title,
            "description": new_quiz.description,
            "accessCode": new_quiz.quiz_access_code or ""
        },
        "subscription": {
            "quizzesUsed": subscription.quizzes_used,
            "quizzesRemaining": subscription.quiz_limit - subscription.quizzes_used
        }
    })
"""


# ============================================================================
# STEP 6: ADD TEACHER DASHBOARD ROUTE
# ============================================================================
"""
# Add a new route for teacher dashboard:

@app.route('/teacher-dashboard')
def teacher_dashboard_page():
    \"\"\"Teacher dashboard page\"\"\"
    return send_from_directory('.', 'teacher-dashboard.html')


@app.route('/api/teacher/dashboard')
def teacher_dashboard_data():
    \"\"\"Get teacher dashboard data\"\"\"
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False, 
            "message": "Authentication required"
        }), 401
    
    user = SubscriptionUser.query.get(user_id)
    
    if not user or user.role != 'teacher':
        return jsonify({
            "success": False, 
            "message": "Teacher access required"
        }), 403
    
    return jsonify({
        "success": True,
        "user": user.to_dict()
    })
"""


# ============================================================================
# STEP 7: ADD PAYMENT MANAGEMENT PAGE ROUTE
# ============================================================================
"""
# Add route for payment management page:

@app.route('/admin/payments')
def admin_payments_page():
    \"\"\"Admin payment management page\"\"\"
    return send_from_directory('.', 'admin-payments.html')
"""


# ============================================================================
# STEP 8: ADD SESSION INITIALIZATION
# ============================================================================
"""
# Add secret key for sessions if not already present:

if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
"""


# ============================================================================
# COMPLETE INTEGRATION EXAMPLE
# ============================================================================
"""
Here's how your updated app.py should look (relevant sections):

```python
from flask import Flask, jsonify, request, send_from_directory, Response, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import json
import csv
import io
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask_mail import Mail, Message
import uuid

# [ADD] Import subscription modules
from models.subscription_models import (
    db, SubscriptionPlan, Payment, UserSubscription, 
    AdminAuditLog, RateLimitLog, User as SubscriptionUser
)
from routes.subscription_routes import subscription_bp
from utils.email_utils import get_mail_config

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', '...')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# [UPDATED] Mail configuration
app.config.update(get_mail_config())
db = SQLAlchemy(app)
mail = Mail(app)

# [ADD] Initialize subscription models
init_subscription_models(app)

# [ADD] Register subscription blueprint
app.register_blueprint(subscription_bp)

# ... rest of your existing code ...

# Update admin login to support teachers
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    # ... updated code from Step 4 ...

# Update create_quiz to enforce limits
@app.route('/api/admin/quiz', methods=['POST'])
def create_quiz():
    # ... updated code from Step 5 ...

# Add new routes
@app.route('/teacher-dashboard')
def teacher_dashboard_page():
    return send_from_directory('.', 'teacher-dashboard.html')

@app.route('/admin/payments')
def admin_payments_page():
    return send_from_directory('.', 'admin-payments.html')

if __name__ == '__main__':
    app.run(debug=True)
```
"""


# ============================================================================
# ENVIRONMENT VARIABLES TO ADD TO .env
# ============================================================================
"""
# Add these to your .env file:

SECRET_KEY=your-super-secret-key-change-this-in-production
MAIL_SERVER=mail.spacemail.com
MAIL_PORT=465
MAIL_USE_SSL=true
MAIL_USE_TLS=false
MAIL_USERNAME=noreply@quizflow.buzz
MAIL_PASSWORD=your-email-password-here
MAIL_DEFAULT_SENDER=noreply@quizflow.buzz

# Admin credentials (optional - can also use database)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-to-secure-password
"""
