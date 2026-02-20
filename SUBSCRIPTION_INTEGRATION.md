# QuizFlow Subscription System - Integration Guide

## Overview

This document provides step-by-step instructions for integrating the subscription and payment system into your existing QuizFlow application.

## Features Implemented

✅ **Subscription Pricing System**
- 3 monthly plans: Basic (500 BDT), Standard (1000 BDT), Premium (1500 BDT)
- Quiz limits: 10, 15, 20 quizzes/month respectively
- Automatic 30-day renewal cycle
- Subscription expiry and limit enforcement

✅ **bKash Payment Workflow**
- Manual Send Money to: 01759954385
- Payment submission with Transaction ID + Screenshot
- Admin approval/rejection system
- Email notifications at each step

✅ **Automatic Admin Account Creation**
- Secure username/password generation
- Password hashing with Werkzeug
- Email delivery of credentials
- Duplicate email prevention

✅ **SMTP Email Automation**
- Spaceship Spacemail integration
- Role-based mailboxes (support, billing, noreply, admin, partnership)
- Reusable `send_email()` function

✅ **Security Features**
- Rate limiting on payment submissions
- Duplicate transaction ID prevention
- Email validation
- Admin-only approval routes
- Session-based authentication

---

## File Structure

```
QuizFlow/
├── models/
│   ├── __init__.py
│   └── subscription_models.py      # Database models
├── routes/
│   ├── __init__.py
│   └── subscription_routes.py      # API endpoints
├── utils/
│   ├── __init__.py
│   └── email_utils.py              # Email & password utilities
├── pricing.html                     # Pricing plans page
├── payment.html                     # Payment submission form
├── teacher-dashboard.html           # Teacher dashboard
├── admin-payments.html              # Admin payment management
├── subscription_migration.sql       # Database migration
├── INTEGRATION_GUIDE.py             # Code integration guide
└── SUBSCRIPTION_INTEGRATION.md      # This file
```

---

## Step 1: Database Setup

Run the database migration to create required tables:

```bash
# Connect to your PostgreSQL database
psql -h <host> -U <username> -d <database>

# Run the migration
\i subscription_migration.sql
```

Or execute via Python:

```python
import psycopg2

conn = psycopg2.connect("your-connection-string")
with open('subscription_migration.sql', 'r') as f:
    conn.execute(f.read())
conn.commit()
conn.close()
```

### Tables Created:
- `subscription_plans` - Plan definitions
- `payments` - Payment records
- `user_subscriptions` - Active subscriptions
- `admin_audit_log` - Admin action logging
- `rate_limit_log` - Rate limiting

---

## Step 2: Update app.py

### 2.1 Add Imports

Add these imports at the top of `app.py`:

```python
# Add after existing imports
from models.subscription_models import (
    db, SubscriptionPlan, Payment, UserSubscription, 
    AdminAuditLog, RateLimitLog, User as SubscriptionUser,
    init_subscription_models
)
from routes.subscription_routes import subscription_bp
from utils.email_utils import get_mail_config
from datetime import datetime, timezone, timedelta
from flask import session  # If not already imported
```

### 2.2 Add Secret Key

Add this after creating the Flask app:

```python
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)
```

### 2.3 Update Mail Configuration

Replace or update your mail configuration:

```python
# Existing mail config - replace with:
app.config.update(get_mail_config())
mail = Mail(app)
```

### 2.4 Initialize Subscription System

Add before `if __name__ == '__main____':`:

```python
# Initialize subscription models
init_subscription_models(app)

# Register subscription blueprint
app.register_blueprint(subscription_bp)
```

### 2.5 Update Admin Login Route

Replace your existing `/api/admin/login` route with:

```python
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin/Teacher authentication endpoint"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    username = data.get('username', '')
    password = data.get('password', '')

    # Check teacher/admin users in database first
    user = SubscriptionUser.query.filter(
        (SubscriptionUser.username == username) | (SubscriptionUser.email == username)
    ).first()
    
    if user and user.check_password(password):
        if user.role in ['teacher', 'admin']:
            # Store user info in session
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
    
    # Fallback to environment variable admin credentials
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
```

### 2.6 Update Create Quiz Route

Replace your existing `/api/admin/quiz` route with the version that includes subscription enforcement (see `INTEGRATION_GUIDE.py` Step 5 for full code).

### 2.7 Add New Page Routes

Add these routes for the new pages:

```python
@app.route('/teacher-dashboard')
def teacher_dashboard_page():
    """Teacher dashboard page"""
    return send_from_directory('.', 'teacher-dashboard.html')

@app.route('/admin/payments')
def admin_payments_page():
    """Admin payment management page"""
    return send_from_directory('.', 'admin-payments.html')
```

---

## Step 3: Environment Variables

Create or update your `.env` file:

```env
# Flask Session
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database (existing)
DATABASE_URL=postgresql://...

# Email Configuration - Spaceship Spacemail
MAIL_SERVER=mail.spacemail.com
MAIL_PORT=465
MAIL_USE_SSL=true
MAIL_USE_TLS=false
MAIL_USERNAME=noreply@quizflow.buzz
MAIL_PASSWORD=your-email-password-here
MAIL_DEFAULT_SENDER=noreply@quizflow.buzz

# Admin Credentials (fallback)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-to-secure-password

# bKash Number (for display)
BKASH_NUMBER=01759954385
```

---

## Step 4: Update Admin Dashboard

Add a link to the payment management page in your `admin.html`:

```html
<!-- Add to the sidebar navigation -->
<li class="admin-nav-item">
    <a href="#" class="admin-nav-link" onclick="switchTab('payments', this)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="5" width="20" height="14" rx="2"/>
            <line x1="2" y1="10" x2="22" y2="10"/>
        </svg>
        Payments
    </a>
</li>

<!-- Add tab content area -->
<div id="payments" class="tab-content">
    <div class="card">
        <div class="card-header">
            <h3>Payment Management</h3>
        </div>
        <div style="padding: 2rem; text-align: center;">
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
                Manage subscription payments in the dedicated payment dashboard
            </p>
            <a href="/admin/payments" class="btn btn-primary">
                Open Payment Dashboard
            </a>
        </div>
    </div>
</div>
```

---

## Step 5: Testing

### 5.1 Test Subscription Plans API

```bash
curl http://localhost:5000/api/subscription/plans
```

Expected response:
```json
{
  "success": true,
  "plans": [
    {"planName": "Basic", "price": 500, "quizLimit": 10},
    {"planName": "Standard", "price": 1000, "quizLimit": 15},
    {"planName": "Premium", "price": 1500, "quizLimit": 20}
  ]
}
```

### 5.2 Test Payment Submission

1. Navigate to `/pricing.html`
2. Select a plan
3. Fill in payment form with test data
4. Submit

### 5.3 Test Admin Approval

1. Login to admin dashboard
2. Navigate to Payments
3. View pending payment
4. Click "Approve Payment"
5. Check email for credentials

### 5.4 Test Quiz Creation Limit

1. Login as teacher
2. Create quizzes until limit reached
3. Verify error message on next attempt

---

## API Endpoints Reference

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subscription/plans` | Get all subscription plans |
| GET | `/api/subscription/plan/<name>` | Get specific plan |
| POST | `/api/payment/submit` | Submit payment |
| GET | `/api/payment/status/<trx_id>` | Check payment status |

### Teacher Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subscription/status` | Get subscription status |
| GET | `/api/subscription/can-create-quiz` | Check quiz creation permission |
| POST | `/api/subscription/increment-usage` | Increment quiz usage |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/payments/pending` | Get pending payments |
| GET | `/api/admin/payments/all` | Get all payments |
| POST | `/api/admin/payment/<id>/approve` | Approve payment |
| POST | `/api/admin/payment/<id>/reject` | Reject payment |
| GET | `/api/admin/payment/<id>/screenshot` | View screenshot |
| GET | `/api/admin/teachers` | Get all teachers |
| POST | `/api/admin/teacher/<id>/upgrade` | Upgrade teacher plan |
| POST | `/api/admin/teacher/<id>/deactivate` | Deactivate teacher |
| GET | `/api/admin/audit-log` | Get audit log |

---

## Email Templates

The system sends these automated emails:

1. **Payment Confirmation** - Sent when user submits payment
2. **Account Creation** - Sent when admin approves payment (includes credentials)
3. **Payment Approved** - Notification of approval
4. **Payment Rejected** - Notification with rejection reason

All emails use the role-based mailboxes:
- `billing@quizflow.buzz` - Payment-related emails
- `noreply@quizflow.buzz` - Account creation emails
- `support@quizflow.buzz` - Support communications

---

## Security Considerations

### Password Security
- All passwords hashed using Werkzeug's `generate_password_hash()`
- Secure random password generation (12+ characters)
- Includes uppercase, lowercase, digits, and special characters

### Rate Limiting
- 5 payment submissions per hour per email/IP
- Logged in `rate_limit_log` table

### Session Security
- Session-based authentication
- Secret key required for session encryption
- Admin-only routes protected with decorators

### Input Validation
- Email format validation
- Transaction ID uniqueness check
- Amount verification against plan price

---

## Troubleshooting

### Database Connection Issues
```python
# Test database connection
from models.subscription_models import db
with app.app_context():
    db.create_all()
    print("Database connection successful")
```

### Email Sending Issues
```python
# Test email configuration
from utils.email_utils import send_email
with app.app_context():
    result = send_email('test@example.com', 'Test', 'Test message')
    print(result)
```

### Subscription Not Enforced
1. Check `init_subscription_models(app)` is called
2. Verify blueprint is registered
3. Check session is properly configured
4. Ensure user role is 'teacher'

---

## Production Deployment

### Before Deploying

1. Change all default passwords
2. Set strong `SECRET_KEY`
3. Use production email credentials
4. Enable HTTPS
5. Set up database backups
6. Configure error logging

### Vercel Deployment

Update `vercel.json`:
```json
{
  "builds": [{
    "src": "app.py",
    "use": "@vercel/python"
  }],
  "routes": [{
    "src": "/(.*)",
    "dest": "app.py"
  }],
  "env": {
    "SECRET_KEY": "@secret-key",
    "MAIL_PASSWORD": "@mail-password"
  }
}
```

Add environment variables in Vercel dashboard.

---

## Support

For issues or questions:
- 📧 Email: support@quizflow.buzz
- 💳 Billing: billing@quizflow.buzz

---

## Changelog

### Version 1.0.0
- Initial subscription system release
- 3-tier pricing (Basic, Standard, Premium)
- bKash payment integration
- Admin approval workflow
- Email automation
- Quiz limit enforcement
