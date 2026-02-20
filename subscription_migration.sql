-- QuizFlow Subscription System Database Migration
-- Run this script to add subscription, payment, and enhanced user tables

-- ============================================================================
-- 1. SUBSCRIPTION PLANS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_name VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'BDT',
    quiz_limit INTEGER NOT NULL,
    duration_days INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default subscription plans
INSERT INTO subscription_plans (plan_name, price, quiz_limit, duration_days, is_active) VALUES
    ('Basic', 500.00, 10, 30, TRUE),
    ('Standard', 1000.00, 15, 30, TRUE),
    ('Premium', 1500.00, 20, 30, TRUE)
ON CONFLICT (plan_name) DO UPDATE SET
    price = EXCLUDED.price,
    quiz_limit = EXCLUDED.quiz_limit,
    duration_days = EXCLUDED.duration_days,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. PAYMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    trx_id VARCHAR(50) UNIQUE NOT NULL,
    screenshot_path VARCHAR(500),
    screenshot_data BYTEA,
    plan_name VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by INTEGER,
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_email ON payments(user_email);
CREATE INDEX IF NOT EXISTS idx_payments_trx_id ON payments(trx_id);
CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at);

-- ============================================================================
-- 3. USER SUBSCRIPTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_name VARCHAR(50) NOT NULL,
    quiz_limit INTEGER NOT NULL,
    quizzes_used INTEGER DEFAULT 0,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    payment_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    CONSTRAINT chk_quiz_usage CHECK (quizzes_used >= 0 AND quizzes_used <= quiz_limit)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_expiry ON user_subscriptions(expiry_date);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_active ON user_subscriptions(is_active);

-- ============================================================================
-- 4. ADD SUBSCRIPTION FIELDS TO USERS TABLE
-- ============================================================================
-- Add role column if not exists
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'student';
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100) UNIQUE;

-- Add subscription tracking columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_limit INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quizzes_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expiry TIMESTAMP;

-- Set default role for existing users
UPDATE users SET role = 'student' WHERE role IS NULL;

-- ============================================================================
-- 5. ADMIN AUDIT LOG TABLE (for tracking payment approvals)
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_username VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id INTEGER,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_admin ON admin_audit_log(admin_username);
CREATE INDEX IF NOT EXISTS idx_admin_audit_action ON admin_audit_log(action);

-- ============================================================================
-- 6. RATE LIMITING TABLE (for payment submissions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_log (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_identifier ON rate_limit_log(identifier);
CREATE INDEX IF NOT EXISTS idx_rate_limit_time ON rate_limit_log(attempted_at);

-- ============================================================================
-- 7. HELPER VIEWS
-- ============================================================================
-- View for active subscriptions with user info
CREATE OR REPLACE VIEW active_subscriptions_view AS
SELECT 
    u.id AS user_id,
    u.email,
    u.username,
    u.name,
    us.plan_name,
    us.quiz_limit,
    us.quizzes_used,
    (us.quiz_limit - us.quizzes_used) AS quizzes_remaining,
    us.start_date,
    us.expiry_date,
    us.is_active,
    CASE 
        WHEN us.expiry_date < CURRENT_TIMESTAMP THEN 'expired'
        WHEN us.quizzes_used >= us.quiz_limit THEN 'limit_reached'
        ELSE 'active'
    END AS subscription_status
FROM users u
JOIN user_subscriptions us ON u.id = us.user_id
WHERE us.is_active = TRUE
ORDER BY us.expiry_date;

-- View for pending payments
CREATE OR REPLACE VIEW pending_payments_view AS
SELECT 
    p.id,
    p.user_email,
    p.trx_id,
    p.plan_name,
    p.amount,
    p.created_at,
    u.name AS user_name
FROM payments p
LEFT JOIN users u ON p.user_email = u.email
WHERE p.status = 'pending'
ORDER BY p.created_at DESC;

-- ============================================================================
-- 8. TRIGGER FUNCTIONS
-- ============================================================================
-- Function to update user subscription fields when user_subscriptions changes
CREATE OR REPLACE FUNCTION update_user_subscription_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE users 
        SET 
            plan = NEW.plan_name,
            quiz_limit = NEW.quiz_limit,
            quizzes_used = NEW.quizzes_used,
            subscription_expiry = NEW.expiry_date
        WHERE id = NEW.user_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE users 
        SET 
            plan = 'free',
            quiz_limit = 0,
            quizzes_used = 0,
            subscription_expiry = NULL
        WHERE id = OLD.user_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_update_user_subscription ON user_subscriptions;
CREATE TRIGGER trg_update_user_subscription
AFTER INSERT OR UPDATE OR DELETE ON user_subscriptions
FOR EACH ROW EXECUTE FUNCTION update_user_subscription_fields();

-- Function to reset quiz limit every 30 days
CREATE OR REPLACE FUNCTION reset_quiz_limits()
RETURNS VOID AS $$
BEGIN
    UPDATE user_subscriptions
    SET 
        quizzes_used = 0,
        start_date = expiry_date,
        expiry_date = expiry_date + (duration_days || ' days')::INTERVAL
    WHERE expiry_date <= CURRENT_TIMESTAMP
    AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
SELECT 'Subscription plans created: ' || COUNT(*) AS status FROM subscription_plans;
SELECT 'Payments table created' AS status FROM payments LIMIT 1;
SELECT 'User subscriptions table created' AS status FROM user_subscriptions LIMIT 1;
SELECT 'Admin audit log table created' AS status FROM admin_audit_log LIMIT 1;
SELECT 'Rate limit log table created' AS status FROM rate_limit_log LIMIT 1;
