"""
QuizFlow Subscription System - Database Models
=============================================
This module contains all database models for the subscription and payment system.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

db = SQLAlchemy()


# ============================================================================
# SUBSCRIPTION PLAN MODEL
# ============================================================================
class SubscriptionPlan(db.Model):
    """
    Subscription plans available for purchase.
    Predefined plans: Basic (500 BDT), Standard (1000 BDT), Premium (1500 BDT)
    """
    __tablename__ = 'subscription_plans'

    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='BDT')
    quiz_limit = db.Column(db.Integer, nullable=False)
    duration_days = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationship with user subscriptions
    subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)

    def to_dict(self):
        """Convert plan to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'planName': self.plan_name,
            'price': float(self.price),
            'currency': self.currency,
            'quizLimit': self.quiz_limit,
            'durationDays': self.duration_days,
            'isActive': self.is_active
        }

    @classmethod
    def get_plan_by_name(cls, plan_name):
        """Get a subscription plan by name"""
        return cls.query.filter_by(plan_name=plan_name, is_active=True).first()

    @classmethod
    def get_all_active_plans(cls):
        """Get all active subscription plans"""
        return cls.query.filter_by(is_active=True).all()


# ============================================================================
# PAYMENT MODEL
# ============================================================================
class Payment(db.Model):
    """
    Payment records for subscription purchases.
    Stores bKash transaction details and screenshots.
    """
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), nullable=False, index=True)
    trx_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    screenshot_path = db.Column(db.String(500))
    screenshot_data = db.Column(db.LargeBinary)  # Store screenshot as binary
    plan_name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    approved_by = db.Column(db.Integer)  # Admin user ID who approved
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationship with user subscription
    user_subscription = db.relationship('UserSubscription', backref='payment', lazy=True, uselist=False)

    def to_dict(self, include_screenshot=False):
        """Convert payment to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'userEmail': self.user_email,
            'trxId': self.trx_id,
            'planName': self.plan_name,
            'amount': float(self.amount),
            'status': self.status,
            'approvedBy': self.approved_by,
            'approvedAt': self.approved_at.isoformat() if self.approved_at else None,
            'rejectionReason': self.rejection_reason,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'hasScreenshot': bool(self.screenshot_data or self.screenshot_path)
        }
        return data

    @classmethod
    def get_pending_payments(cls):
        """Get all pending payments for admin review"""
        return cls.query.filter_by(status='pending').order_by(cls.created_at.desc()).all()

    @classmethod
    def get_by_trx_id(cls, trx_id):
        """Get payment by transaction ID"""
        return cls.query.filter_by(trx_id=trx_id).first()

    @classmethod
    def get_by_email(cls, email):
        """Get all payments by user email"""
        return cls.query.filter_by(user_email=email).order_by(cls.created_at.desc()).all()

    def approve(self, admin_id):
        """Approve this payment"""
        self.status = 'approved'
        self.approved_by = admin_id
        self.approved_at = datetime.now(timezone.utc)
        db.session.commit()

    def reject(self, admin_id, reason):
        """Reject this payment with a reason"""
        self.status = 'rejected'
        self.approved_by = admin_id
        self.approved_at = datetime.now(timezone.utc)
        self.rejection_reason = reason
        db.session.commit()


# ============================================================================
# USER SUBSCRIPTION MODEL
# ============================================================================
class UserSubscription(db.Model):
    """
    Active user subscriptions with quiz usage tracking.
    Automatically resets quiz limit every 30 days.
    """
    __tablename__ = 'user_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    plan_name = db.Column(db.String(50), nullable=False)
    quiz_limit = db.Column(db.Integer, nullable=False)
    quizzes_used = db.Column(db.Integer, default=0)
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date = db.Column(db.DateTime, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert subscription to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'userId': self.user_id,
            'planName': self.plan_name,
            'quizLimit': self.quiz_limit,
            'quizzesUsed': self.quizzes_used,
            'quizzesRemaining': self.quiz_limit - self.quizzes_used,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'expiryDate': self.expiry_date.isoformat() if self.expiry_date else None,
            'isActive': self.is_active,
            'status': self.get_status()
        }

    def get_status(self):
        """Get current subscription status"""
        if not self.is_active:
            return 'inactive'
        if self.expiry_date < datetime.now(timezone.utc):
            return 'expired'
        if self.quizzes_used >= self.quiz_limit:
            return 'limit_reached'
        return 'active'

    def can_create_quiz(self):
        """Check if user can create more quizzes"""
        if not self.is_active:
            return False
        if self.expiry_date < datetime.now(timezone.utc):
            return False
        if self.quizzes_used >= self.quiz_limit:
            return False
        return True

    def increment_quiz_usage(self):
        """Increment the quiz usage counter"""
        if self.can_create_quiz():
            self.quizzes_used += 1
            db.session.commit()
            return True
        return False

    def reset_usage(self):
        """Reset quiz usage and extend subscription for another period"""
        self.quizzes_used = 0
        self.start_date = self.expiry_date
        self.expiry_date = self.expiry_date + timedelta(days=self.quiz_limit)
        db.session.commit()

    @classmethod
    def get_active_subscription(cls, user_id):
        """Get active subscription for a user"""
        return cls.query.filter_by(user_id=user_id, is_active=True).first()

    @classmethod
    def get_subscription_status(cls, user_id):
        """Get detailed subscription status for a user"""
        subscription = cls.get_active_subscription(user_id)
        if not subscription:
            return {
                'hasSubscription': False,
                'plan': 'free',
                'quizzesRemaining': 0,
                'quizLimit': 0,
                'quizzesUsed': 0,
                'status': 'no_subscription'
            }
        
        return {
            'hasSubscription': True,
            'plan': subscription.plan_name,
            'quizzesRemaining': subscription.quiz_limit - subscription.quizzes_used,
            'quizLimit': subscription.quiz_limit,
            'quizzesUsed': subscription.quizzes_used,
            'status': subscription.get_status(),
            'expiryDate': subscription.expiry_date.isoformat() if subscription.expiry_date else None
        }


# ============================================================================
# ADMIN AUDIT LOG MODEL
# ============================================================================
class AdminAuditLog(db.Model):
    """
    Audit log for admin actions (payment approvals, rejections, etc.)
    """
    __tablename__ = 'admin_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    admin_username = db.Column(db.String(100), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    target_type = db.Column(db.String(50))  # e.g., 'payment', 'user', 'subscription'
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'adminUsername': self.admin_username,
            'action': self.action,
            'targetType': self.target_type,
            'targetId': self.target_id,
            'details': self.details,
            'ipAddress': self.ip_address,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def log_action(cls, admin_username, action, target_type=None, target_id=None, 
                   details=None, ip_address=None):
        """Log an admin action"""
        log = cls(
            admin_username=admin_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()
        return log


# ============================================================================
# RATE LIMIT LOG MODEL
# ============================================================================
class RateLimitLog(db.Model):
    """
    Rate limiting log to prevent abuse of payment submissions.
    """
    __tablename__ = 'rate_limit_log'

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(255), nullable=False, index=True)  # email or IP
    action = db.Column(db.String(50), nullable=False)
    attempted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = db.Column(db.String(45))

    @classmethod
    def check_rate_limit(cls, identifier, action, max_attempts=5, window_minutes=60):
        """
        Check if identifier has exceeded rate limit.
        Returns True if within limit, False if exceeded.
        """
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        count = cls.query.filter(
            cls.identifier == identifier,
            cls.action == action,
            cls.attempted_at >= window_start
        ).count()
        return count < max_attempts

    @classmethod
    def log_attempt(cls, identifier, action, ip_address=None):
        """Log a rate-limited action attempt"""
        log = cls(
            identifier=identifier,
            action=action,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()


# ============================================================================
# EXTENDED USER MODEL FUNCTIONS
# ============================================================================
class User(db.Model):
    """
    Extended User model with subscription and role fields.
    This extends the existing User model in app.py
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255))
    username = db.Column(db.String(100), unique=True)
    role = db.Column(db.String(20), default='student')  # student, teacher, admin
    plan = db.Column(db.String(50), default='free')
    quiz_limit = db.Column(db.Integer, default=0)
    quizzes_used = db.Column(db.Integer, default=0)
    subscription_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship with subscriptions
    subscriptions = db.relationship('UserSubscription', backref='user', lazy=True)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
        # Keep original password for backward compatibility (consider removing in production)
        self.password = self.password_hash

    def check_password(self, password):
        """Verify password against hash"""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        # Fallback for legacy passwords (consider removing in production)
        return self.password == password

    def is_teacher(self):
        """Check if user has teacher role"""
        return self.role == 'teacher'

    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'

    def get_subscription_status(self):
        """Get user's current subscription status"""
        return UserSubscription.get_subscription_status(self.id)

    def can_create_quiz(self):
        """Check if user can create more quizzes"""
        if not self.is_teacher():
            return False
        
        subscription = UserSubscription.get_active_subscription(self.id)
        if not subscription:
            return False
        
        return subscription.can_create_quiz()

    def to_dict(self, include_subscription=True):
        """Convert user to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'username': self.username,
            'role': self.role,
            'plan': self.plan,
            'quizLimit': self.quiz_limit,
            'quizzesUsed': self.quizzes_used,
            'quizzesRemaining': self.quiz_limit - self.quizzes_used,
            'subscriptionExpiry': self.subscription_expiry.isoformat() if self.subscription_expiry else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_subscription:
            data['subscription'] = self.get_subscription_status()
        
        return data

    @classmethod
    def get_teachers(cls):
        """Get all teacher users"""
        return cls.query.filter_by(role='teacher').all()

    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        return cls.query.filter_by(username=username).first()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def init_subscription_models(app):
    """
    Initialize subscription models with Flask app.
    Call this in your main app.py after creating the Flask app.
    """
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # Create default subscription plans if they don't exist
        default_plans = [
            {'plan_name': 'Basic', 'price': 500.00, 'quiz_limit': 10, 'duration_days': 30},
            {'plan_name': 'Standard', 'price': 1000.00, 'quiz_limit': 15, 'duration_days': 30},
            {'plan_name': 'Premium', 'price': 1500.00, 'quiz_limit': 20, 'duration_days': 30}
        ]
        
        for plan_data in default_plans:
            existing_plan = SubscriptionPlan.get_plan_by_name(plan_data['plan_name'])
            if not existing_plan:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
        
        db.session.commit()
