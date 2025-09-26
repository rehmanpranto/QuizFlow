-- Database Migration Script for QuizFlow
-- This script will fix existing databases to match the required schema

-- Add password column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'password'
    ) THEN
        ALTER TABLE users ADD COLUMN password VARCHAR(255);
        
        -- Set default password for existing users (you may want to update this manually)
        UPDATE users SET password = 'temp_password_' || id WHERE password IS NULL;
        
        -- Make the column NOT NULL
        ALTER TABLE users ALTER COLUMN password SET NOT NULL;
        
        SELECT 'Password column added to users table' as migration_status;
    ELSE
        SELECT 'Password column already exists' as migration_status;
    END IF;
END $$;

-- Ensure all required tables exist with correct structure
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time_limit INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'multiple_choice',
    options JSON,
    correct_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    quiz_id INTEGER REFERENCES quizzes(id),
    answers JSON,
    score DECIMAL(5,2),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data if tables are empty
INSERT INTO quizzes (title, description, time_limit) 
SELECT 'Sample Quiz', 'A sample quiz to test the system', 15
WHERE NOT EXISTS (SELECT 1 FROM quizzes);

-- Add sample questions for the sample quiz
DO $$
DECLARE
    quiz_id INTEGER;
BEGIN
    SELECT id INTO quiz_id FROM quizzes WHERE title = 'Sample Quiz' LIMIT 1;
    
    IF quiz_id IS NOT NULL THEN
        INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
            (quiz_id, 'What is the capital of France?', 'multiple_choice', '["Paris", "London", "Berlin", "Madrid"]', 'Paris'),
            (quiz_id, 'What is 2 + 2?', 'multiple_choice', '["3", "4", "5", "6"]', '4'),
            (quiz_id, 'Explain the concept of gravity.', 'written', '[]', 'Gravity is a fundamental force that attracts objects with mass towards each other.')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

SELECT 'Database migration completed successfully!' as final_status;
