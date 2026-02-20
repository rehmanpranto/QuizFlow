"""
QuizFlow Subscription & Payment API Routes
==========================================
API endpoints for subscription management, payment processing, and teacher accounts.
"""

from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timezone, timedelta
from functools import wraps
import os
import base64
import io

from models.subscription_models import (
    db, SubscriptionPlan, Payment, UserSubscription, 
    AdminAuditLog, User
)
from utils.email_utils import (
    send_account_creation_email,
    send_payment_confirmation_email,
    send_payment_approved_email,
    send_payment_rejected_email,
    send_admin_notification,
    generate_secure_password,
    generate_username_from_email,
    validate_email,
    rate_limit_check,
    get_client_ip,
    MAILBOXES
)

# Create blueprint
subscription_bp = Blueprint('subscription', __name__, url_prefix='/api')


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if admin is logged in (session-based)
        if not session.get('is_admin'):
            return jsonify({
                'success': False,
                'message': 'Admin authentication required'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def require_teacher(f):
    """Decorator to require teacher authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
        
        user = User.query.get(user_id)
        if not user or user.role != 'teacher':
            return jsonify({
                'success': False,
                'message': 'Teacher access required'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# SUBSCRIPTION PLANS ROUTES
# ============================================================================

@subscription_bp.route('/subscription/plans', methods=['GET'])
def get_subscription_plans():
    """
    Get all active subscription plans.
    Public endpoint - no authentication required.
    """
    try:
        plans = SubscriptionPlan.get_all_active_plans()
        return jsonify({
            'success': True,
            'plans': [plan.to_dict() for plan in plans]
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching plans: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch subscription plans'
        }), 500


@subscription_bp.route('/subscription/plan/<plan_name>', methods=['GET'])
def get_subscription_plan(plan_name):
    """
    Get details of a specific subscription plan.
    """
    try:
        plan = SubscriptionPlan.get_plan_by_name(plan_name)
        if not plan:
            return jsonify({
                'success': False,
                'message': f'Plan "{plan_name}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'plan': plan.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching plan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch plan details'
        }), 500


# ============================================================================
# PAYMENT SUBMISSION ROUTES
# ============================================================================

@subscription_bp.route('/payment/submit', methods=['POST'])
def submit_payment():
    """
    Submit a payment for subscription.
    Rate limited: 5 attempts per hour per email/IP.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body must be JSON'
            }), 400
        
        # Extract and validate fields
        user_email = data.get('email', '').strip().lower()
        trx_id = data.get('trxId', '').strip()
        plan_name = data.get('planName', '').strip()
        amount = data.get('amount')
        screenshot_base64 = data.get('screenshot')  # Base64 encoded image
        
        # Validation
        if not user_email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        if not validate_email(user_email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        if not trx_id:
            return jsonify({'success': False, 'message': 'Transaction ID is required'}), 400
        
        if not plan_name:
            return jsonify({'success': False, 'message': 'Plan name is required'}), 400
        
        if amount is None:
            return jsonify({'success': False, 'message': 'Amount is required'}), 400
        
        # Check rate limit (5 submissions per hour per email)
        client_ip = get_client_ip()
        if not rate_limit_check(user_email, 'payment_submit', max_attempts=5, window_minutes=60):
            return jsonify({
                'success': False,
                'message': 'Too many payment submissions. Please try again in 60 minutes.'
            }), 429
        
        # Check for duplicate transaction ID
        existing_payment = Payment.get_by_trx_id(trx_id)
        if existing_payment:
            return jsonify({
                'success': False,
                'message': 'This transaction ID has already been submitted'
            }), 400
        
        # Verify plan exists and get correct amount
        plan = SubscriptionPlan.get_plan_by_name(plan_name)
        if not plan:
            return jsonify({
                'success': False,
                'message': f'Invalid plan: {plan_name}'
            }), 400
        
        # Verify amount matches plan price
        try:
            submitted_amount = float(amount)
            plan_amount = float(plan.price)
            # Allow 10% tolerance for currency conversion
            if abs(submitted_amount - plan_amount) > plan_amount * 0.1:
                return jsonify({
                    'success': False,
                    'message': f'Amount does not match plan price. Expected: {plan_amount} BDT'
                }), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        # Process screenshot (optional but recommended)
        screenshot_data = None
        if screenshot_base64:
            try:
                # Remove data:image prefix if present
                if ',' in screenshot_base64:
                    screenshot_base64 = screenshot_base64.split(',')[1]
                screenshot_data = base64.b64decode(screenshot_base64)
            except Exception as e:
                current_app.logger.warning(f"Failed to decode screenshot: {str(e)}")
                # Continue without screenshot
        
        # Create payment record
        payment = Payment(
            user_email=user_email,
            trx_id=trx_id,
            plan_name=plan_name,
            amount=submitted_amount,
            status='pending',
            screenshot_data=screenshot_data
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Send confirmation email to user
        send_payment_confirmation_email(user_email, plan_name, submitted_amount, trx_id)
        
        # Notify admin of new payment
        send_admin_notification(
            subject=f"New Payment Submission - {plan_name}",
            message=f"""
New payment submission received:

Email: {user_email}
Plan: {plan_name}
Amount: {submitted_amount} BDT
Transaction ID: {trx_id}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Please review and approve/reject in the admin dashboard.
            """,
            admin_emails=[MAILBOXES['billing']]
        )
        
        current_app.logger.info(f"Payment submitted: {trx_id} by {user_email}")
        
        return jsonify({
            'success': True,
            'message': 'Payment submitted successfully. Please wait for confirmation.',
            'paymentId': payment.id,
            'trxId': trx_id
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Payment submission error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to submit payment. Please try again.'
        }), 500


@subscription_bp.route('/payment/status/<trx_id>', methods=['GET'])
def get_payment_status(trx_id):
    """
    Get payment status by transaction ID.
    """
    try:
        payment = Payment.get_by_trx_id(trx_id)
        
        if not payment:
            return jsonify({
                'success': False,
                'message': 'Payment not found'
            }), 404
        
        return jsonify({
            'success': True,
            'payment': {
                'trxId': payment.trx_id,
                'planName': payment.plan_name,
                'amount': float(payment.amount),
                'status': payment.status,
                'submittedAt': payment.created_at.isoformat() if payment.created_at else None,
                'approvedAt': payment.approved_at.isoformat() if payment.approved_at else None,
                'rejectionReason': payment.rejection_reason
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching payment status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch payment status'
        }), 500


@subscription_bp.route('/payment/my-payments', methods=['GET'])
def get_my_payments():
    """
    Get all payments for the authenticated user.
    """
    try:
        # Get email from session or query parameter
        email = session.get('user_email') or request.args.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email required'
            }), 400
        
        payments = Payment.get_by_email(email)
        
        return jsonify({
            'success': True,
            'payments': [p.to_dict() for p in payments]
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching payments: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch payments'
        }), 500


# ============================================================================
# ADMIN PAYMENT MANAGEMENT ROUTES
# ============================================================================

@subscription_bp.route('/admin/payments/pending', methods=['GET'])
@require_admin
def get_pending_payments():
    """
    Get all pending payments for admin review.
    """
    try:
        payments = Payment.get_pending_payments()
        
        return jsonify({
            'success': True,
            'payments': [p.to_dict() for p in payments]
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching pending payments: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch pending payments'
        }), 500


@subscription_bp.route('/admin/payments/all', methods=['GET'])
@require_admin
def get_all_payments():
    """
    Get all payments (for admin dashboard).
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')  # Optional filter
        
        query = Payment.query.order_by(Payment.created_at.desc())
        
        if status:
            query = query.filter_by(status=status)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        payments = pagination.items
        
        return jsonify({
            'success': True,
            'payments': [p.to_dict() for p in payments],
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching all payments: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch payments'
        }), 500


@subscription_bp.route('/admin/payment/<int:payment_id>/approve', methods=['POST'])
@require_admin
def approve_payment(payment_id):
    """
    Approve a payment and create teacher account.
    """
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'pending':
            return jsonify({
                'success': False,
                'message': f'Payment already {payment.status}'
            }), 400
        
        # Check if user already exists
        user = User.get_by_email(payment.user_email)
        
        if user:
            # User exists - check if already a teacher
            if user.role == 'teacher':
                return jsonify({
                    'success': False,
                    'message': 'User is already a teacher'
                }), 400
        else:
            # Create new teacher account
            username = generate_username_from_email(payment.user_email)
            password = generate_secure_password()
            
            # Check username uniqueness
            while User.get_by_username(username):
                username = generate_username_from_email(payment.user_email)
            
            user = User(
                name=payment.user_email.split('@')[0],  # Use email prefix as name
                email=payment.user_email,
                username=username,
                role='teacher',
                password=password  # Will be hashed by model
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Get user ID
        
        # Calculate expiry date
        plan = SubscriptionPlan.get_plan_by_name(payment.plan_name)
        duration_days = plan.duration_days if plan else 30
        expiry_date = datetime.now(timezone.utc) + timedelta(days=duration_days)
        
        # Create user subscription
        subscription = UserSubscription(
            user_id=user.id,
            plan_name=payment.plan_name,
            quiz_limit=plan.quiz_limit if plan else 10,
            expiry_date=expiry_date,
            payment_id=payment.id,
            is_active=True
        )
        db.session.add(subscription)
        
        # Approve payment
        payment.approve(session.get('admin_id') or 1)
        
        # Log admin action
        AdminAuditLog.log_action(
            admin_username=session.get('admin_username') or 'admin',
            action='approve_payment',
            target_type='payment',
            target_id=payment.id,
            details=f'Approved payment {payment.trx_id} for {payment.user_email}',
            ip_address=get_client_ip()
        )
        
        db.session.commit()
        
        # Send account creation email
        send_account_creation_email(
            user_email=user.email,
            username=user.username,
            password=password,
            plan_name=payment.plan_name,
            expiry_date=expiry_date
        )
        
        # Send approval notification
        send_payment_approved_email(user.email, payment.plan_name)
        
        current_app.logger.info(f"Payment approved: {payment.trx_id} -> {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Payment approved and teacher account created',
            'user': {
                'email': user.email,
                'username': user.username,
                'plan': payment.plan_name,
                'expiryDate': expiry_date.isoformat()
            }
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Payment approval error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to approve payment: {str(e)}'
        }), 500


@subscription_bp.route('/admin/payment/<int:payment_id>/reject', methods=['POST'])
@require_admin
def reject_payment(payment_id):
    """
    Reject a payment with a reason.
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'pending':
            return jsonify({
                'success': False,
                'message': f'Payment already {payment.status}'
            }), 400
        
        # Reject payment
        payment.reject(session.get('admin_id') or 1, reason)
        
        # Log admin action
        AdminAuditLog.log_action(
            admin_username=session.get('admin_username') or 'admin',
            action='reject_payment',
            target_type='payment',
            target_id=payment.id,
            details=f'Rejected payment {payment.trx_id}: {reason}',
            ip_address=get_client_ip()
        )
        
        db.session.commit()
        
        # Send rejection email
        send_payment_rejected_email(payment.user_email, reason)
        
        current_app.logger.info(f"Payment rejected: {payment.trx_id} - {reason}")
        
        return jsonify({
            'success': True,
            'message': 'Payment rejected'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Payment rejection error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to reject payment: {str(e)}'
        }), 500


@subscription_bp.route('/admin/payment/<int:payment_id>/screenshot', methods=['GET'])
@require_admin
def get_payment_screenshot(payment_id):
    """
    Get payment screenshot image.
    """
    try:
        from flask import send_file
        
        payment = Payment.query.get_or_404(payment_id)
        
        if not payment.screenshot_data:
            return jsonify({
                'success': False,
                'message': 'No screenshot available'
            }), 404
        
        # Send image
        return send_file(
            io.BytesIO(payment.screenshot_data),
            mimetype='image/png',
            as_attachment=True,
            download_name=f'screenshot_{payment.trx_id}.png'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error fetching screenshot: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch screenshot'
        }), 500


# ============================================================================
# USER SUBSCRIPTION ROUTES
# ============================================================================

@subscription_bp.route('/subscription/status', methods=['GET'])
def get_subscription_status():
    """
    Get current user's subscription status.
    """
    try:
        email = session.get('user_email') or request.args.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email required'
            }), 400
        
        user = User.get_by_email(email)
        
        if not user:
            return jsonify({
                'success': True,
                'subscription': {
                    'hasSubscription': False,
                    'plan': 'free',
                    'quizzesRemaining': 0,
                    'quizLimit': 0,
                    'quizzesUsed': 0,
                    'status': 'no_subscription'
                }
            })
        
        return jsonify({
            'success': True,
            'subscription': user.get_subscription_status()
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching subscription status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch subscription status'
        }), 500


@subscription_bp.route('/subscription/can-create-quiz', methods=['GET'])
def can_create_quiz():
    """
    Check if user can create a new quiz.
    """
    try:
        email = session.get('user_email') or request.args.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email required'
            }), 400
        
        user = User.get_by_email(email)
        
        if not user:
            return jsonify({
                'success': True,
                'canCreate': False,
                'reason': 'User not found'
            })
        
        can_create = user.can_create_quiz()
        subscription = UserSubscription.get_active_subscription(user.id)
        
        reason = None
        if not can_create:
            if user.role != 'teacher':
                reason = 'Only teachers can create quizzes'
            elif not subscription:
                reason = 'No active subscription'
            elif subscription.expiry_date < datetime.now(timezone.utc):
                reason = 'Subscription expired'
            elif subscription.quizzes_used >= subscription.quiz_limit:
                reason = 'Quiz limit reached'
        
        return jsonify({
            'success': True,
            'canCreate': can_create,
            'reason': reason,
            'subscription': subscription.to_dict() if subscription else None
        })
    
    except Exception as e:
        current_app.logger.error(f"Error checking quiz creation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to check quiz creation permission'
        }), 500


@subscription_bp.route('/subscription/increment-usage', methods=['POST'])
@require_teacher
def increment_quiz_usage():
    """
    Increment quiz usage counter when a new quiz is created.
    """
    try:
        user_id = session.get('user_id')
        
        subscription = UserSubscription.get_active_subscription(user_id)
        
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'No active subscription'
            }), 400
        
        if not subscription.can_create_quiz():
            return jsonify({
                'success': False,
                'message': 'Quiz limit reached or subscription expired'
            }), 400
        
        subscription.increment_quiz_usage()
        
        return jsonify({
            'success': True,
            'quizzesUsed': subscription.quizzes_used,
            'quizzesRemaining': subscription.quiz_limit - subscription.quizzes_used
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error incrementing usage: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to increment quiz usage'
        }), 500


# ============================================================================
# ADMIN TEACHER MANAGEMENT ROUTES
# ============================================================================

@subscription_bp.route('/admin/teachers', methods=['GET'])
@require_admin
def get_all_teachers():
    """
    Get all teacher accounts.
    """
    try:
        teachers = User.get_teachers()
        
        return jsonify({
            'success': True,
            'teachers': [t.to_dict() for t in teachers]
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching teachers: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch teachers'
        }), 500


@subscription_bp.route('/admin/teacher/<int:user_id>/upgrade', methods=['POST'])
@require_admin
def upgrade_teacher_plan(user_id):
    """
    Manually upgrade/downgrade a teacher's plan.
    """
    try:
        data = request.get_json()
        plan_name = data.get('planName')
        extend_days = data.get('extendDays', 30)
        
        if not plan_name:
            return jsonify({
                'success': False,
                'message': 'Plan name required'
            }), 400
        
        user = User.query.get_or_404(user_id)
        
        if user.role != 'teacher':
            return jsonify({
                'success': False,
                'message': 'User is not a teacher'
            }), 400
        
        plan = SubscriptionPlan.get_plan_by_name(plan_name)
        if not plan:
            return jsonify({
                'success': False,
                'message': f'Invalid plan: {plan_name}'
            }), 400
        
        # Get or create subscription
        subscription = UserSubscription.get_active_subscription(user_id)
        
        if subscription:
            # Update existing
            subscription.plan_name = plan_name
            subscription.quiz_limit = plan.quiz_limit
            subscription.expiry_date = subscription.expiry_date + timedelta(days=extend_days)
        else:
            # Create new
            expiry_date = datetime.now(timezone.utc) + timedelta(days=extend_days)
            subscription = UserSubscription(
                user_id=user_id,
                plan_name=plan_name,
                quiz_limit=plan.quiz_limit,
                expiry_date=expiry_date,
                is_active=True
            )
            db.session.add(subscription)
        
        db.session.commit()
        
        # Log admin action
        AdminAuditLog.log_action(
            admin_username=session.get('admin_username') or 'admin',
            action='upgrade_teacher',
            target_type='user',
            target_id=user_id,
            details=f'Upgraded {user.email} to {plan_name}',
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'success': True,
            'message': f'Teacher upgraded to {plan_name}',
            'subscription': subscription.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error upgrading teacher: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to upgrade teacher: {str(e)}'
        }), 500


@subscription_bp.route('/admin/teacher/<int:user_id>/deactivate', methods=['POST'])
@require_admin
def deactivate_teacher(user_id):
    """
    Deactivate a teacher's subscription.
    """
    try:
        user = User.query.get_or_404(user_id)
        
        subscription = UserSubscription.get_active_subscription(user_id)
        
        if subscription:
            subscription.is_active = False
            db.session.commit()
        
        # Log admin action
        AdminAuditLog.log_action(
            admin_username=session.get('admin_username') or 'admin',
            action='deactivate_teacher',
            target_type='user',
            target_id=user_id,
            details=f'Deactivated {user.email}',
            ip_address=get_client_ip()
        )
        
        return jsonify({
            'success': True,
            'message': 'Teacher subscription deactivated'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating teacher: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to deactivate teacher: {str(e)}'
        }), 500


# ============================================================================
# ADMIN AUDIT LOG ROUTES
# ============================================================================

@subscription_bp.route('/admin/audit-log', methods=['GET'])
@require_admin
def get_audit_log():
    """
    Get admin audit log.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        pagination = AdminAuditLog.query.order_by(
            AdminAuditLog.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in pagination.items],
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching audit log: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch audit log'
        }), 500
