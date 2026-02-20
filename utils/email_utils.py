"""
QuizFlow Utilities
==================
Password generation, email automation, and security utilities.
"""

import secrets
import string
import re
import os
from datetime import datetime, timezone
from flask import request
from flask_mail import Mail, Message
from functools import wraps


# ============================================================================
# MAIL CONFIGURATION
# ============================================================================

# Role-based mailboxes
MAILBOXES = {
    'support': 'support@quizflow.buzz',
    'billing': 'billing@quizflow.buzz',
    'noreply': 'noreply@quizflow.buzz',
    'admin': 'admin@quizflow.buzz',
    'partnership': 'partnership@quizflow.buzz'
}

# SMTP Configuration (Spaceship Spacemail)
SMTP_CONFIG = {
    'server': 'mail.spacemail.com',
    'port': 465,
    'use_ssl': True,
    'use_tls': False
}


def get_mail_config():
    """
    Get mail configuration from environment variables.
    Returns a dictionary suitable for Flask-Mail configuration.
    """
    return {
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'mail.spacemail.com'),
        'MAIL_PORT': int(os.getenv('MAIL_PORT', 465)),
        'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'false').lower() in ['true', '1', 'yes'],
        'MAIL_USE_SSL': os.getenv('MAIL_USE_SSL', 'true').lower() in ['true', '1', 'yes'],
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME'),
        'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', MAILBOXES['noreply'])
    }


# ============================================================================
# PASSWORD GENERATOR
# ============================================================================

def generate_secure_password(length=12):
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Password length (default: 12 characters)
    
    Returns:
        A secure random password string
    
    The password includes:
    - Uppercase letters (A-Z)
    - Lowercase letters (a-z)
    - Digits (0-9)
    - Special characters (!@#$%^&*)
    """
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = '!@#$%^&*'
    
    # Ensure at least one character from each set
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill remaining length with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    remaining_length = length - 4
    
    if remaining_length > 0:
        password.extend(secrets.choice(all_chars) for _ in range(remaining_length))
    
    # Shuffle the password using secrets for cryptographic randomness
    password_list = list(password)
    # Fisher-Yates shuffle using secrets
    for i in range(len(password_list) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_list[i], password_list[j] = password_list[j], password_list[i]
    
    return ''.join(password_list)


def generate_username_from_email(email):
    """
    Generate a unique username from email address.
    
    Args:
        email: User's email address
    
    Returns:
        A username string (e.g., 'john.doe' from 'john.doe@example.com')
    """
    # Extract part before @
    username = email.split('@')[0]
    
    # Remove special characters except dots and underscores
    username = re.sub(r'[^a-zA-Z0-9._]', '', username)
    
    # Limit length
    username = username[:50]
    
    # Add random suffix for uniqueness
    random_suffix = secrets.token_hex(3)
    username = f"{username}_{random_suffix}"
    
    return username.lower()


# ============================================================================
# EMAIL AUTOMATION
# ============================================================================

def send_email(to, subject, message, html=None, from_mailbox='noreply', cc=None, bcc=None):
    """
    Send an email using Flask-Mail.
    
    Args:
        to: Recipient email address (string or list)
        subject: Email subject
        message: Plain text message body
        html: Optional HTML version of the message
        from_mailbox: Which mailbox to send from (default: 'noreply')
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
    
    Returns:
        dict: {'success': bool, 'message': str}
    
    Usage:
        send_email('user@example.com', 'Welcome', 'Hello!')
        send_email(['user1@example.com', 'user2@example.com'], 'Update', 'News')
    """
    try:
        from flask import current_app
        from flask_mail import Mail, Message
        
        # Get mail instance from app
        mail = current_app.extensions.get('mail')
        
        if not mail:
            return {'success': False, 'message': 'Mail not configured'}
        
        # Get sender address from mailbox
        sender = MAILBOXES.get(from_mailbox, MAILBOXES['noreply'])
        
        # Handle single recipient or list
        recipients = [to] if isinstance(to, str) else to
        
        # Create message
        msg = Message(
            subject=subject,
            sender=sender,
            recipients=recipients,
            body=message,
            html=html,
            cc=cc,
            bcc=bcc
        )
        
        # Send email
        mail.send(msg)
        
        # Log successful send (optional)
        current_app.logger.info(f"Email sent to {recipients} from {sender}: {subject}")
        
        return {'success': True, 'message': 'Email sent successfully'}
    
    except Exception as e:
        # Log error
        if 'current_app' in dir():
            current_app.logger.error(f"Failed to send email: {str(e)}")
        
        return {'success': False, 'message': f'Failed to send email: {str(e)}'}


def send_account_creation_email(user_email, username, password, plan_name, expiry_date):
    """
    Send account creation email to new teacher.
    
    Args:
        user_email: Recipient email
        username: Generated username
        password: Generated password
        plan_name: Subscription plan name
        expiry_date: Subscription expiry date
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    # Format expiry date for display
    if isinstance(expiry_date, datetime):
        expiry_formatted = expiry_date.strftime('%B %d, %Y')
    else:
        expiry_formatted = str(expiry_date)
    
    subject = "🎉 Welcome to QuizFlow - Your Teacher Account is Ready!"
    
    # Plain text version
    text_message = f"""
Welcome to QuizFlow!

Your teacher account has been successfully created.

ACCOUNT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Username: {username}
Password: {password}
Plan: {plan_name}
Subscription Expires: {expiry_formatted}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT SECURITY NOTES:
• Please change your password after first login
• Keep your credentials secure and do not share them
• Your subscription allows you to create quizzes as per your plan limits

GETTING STARTED:
1. Visit: https://quizflow.buzz/admin
2. Login with your credentials above
3. Start creating engaging quizzes for your students!

After sending money please wait up to 2 hours to receive your admin account in your email. 
After that you can start creating quizzes.

Need Help?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Support: support@quizflow.buzz
💳 Billing: billing@quizflow.buzz

Best regards,
The QuizFlow Team
https://quizflow.buzz
"""
    
    # HTML version
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                 background: #050507; color: #f1f5f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.03); 
                     border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 40px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .logo {{ font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #8b5cf6, #6366f1); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .badge {{ display: inline-block; background: rgba(139,92,246,0.15); color: #8b5cf6; 
                 padding: 6px 16px; border-radius: 999px; font-size: 12px; font-weight: 600; 
                 margin-top: 10px; }}
        .credentials {{ background: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.2); 
                       border-radius: 12px; padding: 24px; margin: 24px 0; }}
        .credential-item {{ margin: 16px 0; }}
        .credential-label {{ color: #94a3b8; font-size: 14px; margin-bottom: 4px; }}
        .credential-value {{ font-family: 'SF Mono', monospace; background: rgba(255,255,255,0.05); 
                            padding: 10px 14px; border-radius: 8px; font-size: 15px; 
                            border: 1px solid rgba(255,255,255,0.08); }}
        .plan-badge {{ display: inline-block; background: linear-gradient(135deg, #8b5cf6, #6366f1); 
                      color: #fff; padding: 8px 20px; border-radius: 999px; font-weight: 600; 
                      font-size: 14px; }}
        .section {{ margin: 24px 0; }}
        .section-title {{ color: #8b5cf6; font-size: 12px; text-transform: uppercase; 
                        letter-spacing: 0.1em; margin-bottom: 12px; }}
        .feature-list {{ list-style: none; padding: 0; }}
        .feature-list li {{ padding: 8px 0; color: #94a3b8; font-size: 14px; }}
        .feature-list li::before {{ content: '✓'; color: #34d399; margin-right: 8px; font-weight: bold; }}
        .warning {{ background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); 
                   border-radius: 8px; padding: 16px; margin: 20px 0; font-size: 14px; 
                   color: #fbbf24; }}
        .footer {{ margin-top: 40px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); 
                  text-align: center; color: #475569; font-size: 13px; }}
        .btn {{ display: inline-block; background: linear-gradient(135deg, #8b5cf6, #6366f1); 
               color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 10px; 
               font-weight: 600; margin: 20px 0; }}
        .contact-links {{ margin: 20px 0; }}
        .contact-links a {{ color: #8b5cf6; text-decoration: none; margin: 0 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">QuizFlow</div>
            <div class="badge">Teacher Account Created</div>
        </div>
        
        <h2 style="text-align: center; margin-bottom: 10px;">Welcome to QuizFlow!</h2>
        <p style="text-align: center; color: #94a3b8; margin: 0;">
            Your teacher account has been successfully created
        </p>
        
        <div class="credentials">
            <div class="credential-item">
                <div class="credential-label">Username</div>
                <div class="credential-value">{username}</div>
            </div>
            <div class="credential-item">
                <div class="credential-label">Password</div>
                <div class="credential-value">{password}</div>
            </div>
            <div class="credential-item">
                <div class="credential-label">Subscription Plan</div>
                <div><span class="plan-badge">{plan_name}</span></div>
            </div>
            <div class="credential-item">
                <div class="credential-label">Subscription Expires</div>
                <div class="credential-value">{expiry_formatted}</div>
            </div>
        </div>
        
        <div class="warning">
            <strong>⚠️ Important:</strong> Please change your password after your first login. 
            Keep your credentials secure and do not share them with anyone.
        </div>
        
        <div class="section">
            <div class="section-title">Getting Started</div>
            <ol style="color: #94a3b8; line-height: 1.8;">
                <li>Visit <a href="https://quizflow.buzz/admin" style="color: #8b5cf6;">quizflow.buzz/admin</a></li>
                <li>Login with your credentials above</li>
                <li>Start creating engaging quizzes for your students!</li>
            </ol>
        </div>
        
        <div style="text-align: center;">
            <a href="https://quizflow.buzz/admin" class="btn">Go to Admin Dashboard</a>
        </div>
        
        <div class="section">
            <div class="section-title">Your Plan Includes</div>
            <ul class="feature-list">
                <li>Create up to your plan's quiz limit</li>
                <li>Unlimited student submissions</li>
                <li>Real-time analytics and results</li>
                <li>Email notifications</li>
                <li>24/7 support</li>
            </ul>
        </div>
        
        <div class="contact-links">
            <strong style="color: #94a3b8; font-size: 13px;">Need Help?</strong><br>
            <a href="mailto:support@quizflow.buzz">📧 Support</a>
            <a href="mailto:billing@quizflow.buzz">💳 Billing</a>
        </div>
        
        <div class="footer">
            <p>Best regards,<br>The QuizFlow Team</p>
            <p style="margin-top: 16px;">
                <a href="https://quizflow.buzz" style="color: #475569; text-decoration: none;">quizflow.buzz</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    # Send from noreply mailbox
    return send_email(
        to=user_email,
        subject=subject,
        message=text_message,
        html=html_message,
        from_mailbox='noreply'
    )


def send_payment_confirmation_email(user_email, plan_name, amount, trx_id):
    """
    Send payment submission confirmation to user.
    
    Args:
        user_email: Recipient email
        plan_name: Selected plan name
        amount: Payment amount
        trx_id: Transaction ID
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "✅ Payment Received - QuizFlow Subscription"
    
    text_message = f"""
Thank You for Your Payment!

We have received your payment for QuizFlow subscription.

PAYMENT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Plan: {plan_name}
Amount: {amount} BDT
Transaction ID: {trx_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:
After sending money please wait up to 2 hours to receive your admin account in your email. 
After that you can start creating quizzes.

Account access is only provided after payment confirmation.

WHAT HAPPENS NEXT:
1. Our team will verify your payment (usually within 2 hours)
2. Once approved, you'll receive an email with your teacher account credentials
3. You can then login and start creating quizzes

TRACK YOUR PAYMENT:
You can check the status of your payment by contacting:
📧 billing@quizflow.buzz

Need Help?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Support: support@quizflow.buzz
💳 Billing: billing@quizflow.buzz

Best regards,
The QuizFlow Team
"""
    
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #050507; color: #f1f5f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.03); 
                     border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 40px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .success-icon {{ width: 64px; height: 64px; background: rgba(52,211,153,0.15); 
                        border-radius: 50%; display: inline-flex; align-items: center; 
                        justify-content: center; color: #34d399; font-size: 32px; }}
        .details {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 24px; 
                   margin: 24px 0; }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; 
                      border-bottom: 1px solid rgba(255,255,255,0.08); }}
        .detail-row:last-child {{ border-bottom: none; }}
        .detail-label {{ color: #94a3b8; }}
        .detail-value {{ font-weight: 600; }}
        .info-box {{ background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3); 
                    border-radius: 8px; padding: 16px; margin: 20px 0; color: #818cf8; }}
        .footer {{ margin-top: 40px; text-align: center; color: #475569; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="success-icon">✓</div>
            <h2 style="margin: 16px 0 8px;">Payment Received!</h2>
            <p style="color: #94a3b8; margin: 0;">Thank you for subscribing to QuizFlow</p>
        </div>
        
        <div class="details">
            <div class="detail-row">
                <span class="detail-label">Plan</span>
                <span class="detail-value">{plan_name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Amount</span>
                <span class="detail-value">{amount} BDT</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Transaction ID</span>
                <span class="detail-value" style="font-family: monospace;">{trx_id}</span>
            </div>
        </div>
        
        <div class="info-box">
            <strong>⏱️ Processing Time:</strong><br>
            After sending money please wait up to 2 hours to receive your admin account in your email. 
            After that you can start creating quizzes.
        </div>
        
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
            <strong>Account access is only provided after payment confirmation.</strong><br><br>
            Our team will verify your payment and send your teacher account credentials to this email address.
        </p>
        
        <div class="footer">
            <p>Questions? Contact <a href="mailto:billing@quizflow.buzz" style="color: #8b5cf6;">billing@quizflow.buzz</a></p>
            <p style="margin-top: 16px;">QuizFlow Team</p>
        </div>
    </div>
</body>
</html>
"""
    
    return send_email(
        to=user_email,
        subject=subject,
        message=text_message,
        html=html_message,
        from_mailbox='billing'
    )


def send_payment_approved_email(user_email, plan_name):
    """
    Send payment approval notification.
    
    Args:
        user_email: Recipient email
        plan_name: Approved plan name
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "🎉 Payment Approved - Start Creating Quizzes!"
    
    text_message = f"""
Great News! Your Payment Has Been Approved

Your QuizFlow subscription is now active!

SUBSCRIPTION DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Plan: {plan_name}
Status: Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You should have received a separate email with your teacher account credentials.
If you haven't received it yet, please check your spam folder or contact support.

GET STARTED:
1. Login to your teacher account at: https://quizflow.buzz/admin
2. Navigate to the Quiz Editor
3. Create your first quiz!

Need Help?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Support: support@quizflow.buzz
💳 Billing: billing@quizflow.buzz

Best regards,
The QuizFlow Team
"""
    
    return send_email(
        to=user_email,
        subject=subject,
        message=text_message,
        from_mailbox='billing'
    )


def send_payment_rejected_email(user_email, reason):
    """
    Send payment rejection notification.
    
    Args:
        user_email: Recipient email
        reason: Rejection reason
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "⚠️ Payment Update - QuizFlow Subscription"
    
    text_message = f"""
Payment Update - QuizFlow Subscription

We regret to inform you that your payment could not be approved.

REJECTION REASON:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{reason}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:
1. Please verify your payment details
2. Contact billing@quizflow.buzz with your correct transaction ID
3. We'll process your payment as soon as possible

If you believe this is an error, please reach out to our support team.

Need Help?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Support: support@quizflow.buzz
💳 Billing: billing@quizflow.buzz

Best regards,
The QuizFlow Team
"""
    
    return send_email(
        to=user_email,
        subject=subject,
        message=text_message,
        from_mailbox='billing'
    )


def send_admin_notification(subject, message, admin_emails=None):
    """
    Send notification to admin mailbox.
    
    Args:
        subject: Email subject
        message: Email body
        admin_emails: List of admin emails (optional, uses default if not provided)
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    if admin_emails is None:
        admin_emails = [MAILBOXES['admin']]
    
    return send_email(
        to=admin_emails,
        subject=f"[QuizFlow Admin] {subject}",
        message=message,
        from_mailbox='admin'
    )


# ============================================================================
# SECURITY UTILITIES
# ============================================================================

def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: Email address to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_client_ip():
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def rate_limit_check(identifier, action, max_attempts=5, window_minutes=60):
    """
    Check if action is within rate limit.
    
    Args:
        identifier: User identifier (email or IP)
        action: Action type
        max_attempts: Maximum attempts allowed
        window_minutes: Time window in minutes
    
    Returns:
        bool: True if within limit, False if exceeded
    """
    from models.subscription_models import RateLimitLog, db
    
    # Check if within limit
    if not RateLimitLog.check_rate_limit(identifier, action, max_attempts, window_minutes):
        return False
    
    # Log this attempt
    RateLimitLog.log_attempt(identifier, action, get_client_ip())
    db.session.commit()
    
    return True


def rate_limit_decorator(max_attempts=5, window_minutes=60, action='default'):
    """
    Decorator for rate limiting API endpoints.
    
    Usage:
        @rate_limit_decorator(max_attempts=5, window_minutes=60, action='payment_submit')
        def submit_payment():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import jsonify
            
            # Get identifier (email or IP)
            identifier = request.remote_addr
            data = request.get_json(silent=True)
            if data and 'email' in data:
                identifier = data['email']
            
            # Check rate limit
            if not rate_limit_check(identifier, action, max_attempts, window_minutes):
                return jsonify({
                    'success': False,
                    'message': f'Too many attempts. Please try again in {window_minutes} minutes.'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
