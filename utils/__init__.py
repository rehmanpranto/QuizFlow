"""
QuizFlow Utilities Package
==========================
Email automation, password generation, and security utilities.
"""

from .email_utils import (
    # Mail configuration
    MAILBOXES,
    SMTP_CONFIG,
    get_mail_config,
    
    # Password generation
    generate_secure_password,
    generate_username_from_email,
    
    # Email functions
    send_email,
    send_account_creation_email,
    send_payment_confirmation_email,
    send_payment_approved_email,
    send_payment_rejected_email,
    send_admin_notification,
    
    # Security utilities
    validate_email,
    get_client_ip,
    rate_limit_check,
    rate_limit_decorator
)

__all__ = [
    # Configuration
    'MAILBOXES',
    'SMTP_CONFIG',
    'get_mail_config',
    
    # Password generation
    'generate_secure_password',
    'generate_username_from_email',
    
    # Email functions
    'send_email',
    'send_account_creation_email',
    'send_payment_confirmation_email',
    'send_payment_approved_email',
    'send_payment_rejected_email',
    'send_admin_notification',
    
    # Security utilities
    'validate_email',
    'get_client_ip',
    'rate_limit_check',
    'rate_limit_decorator'
]
