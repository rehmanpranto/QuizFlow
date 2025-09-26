-- QuizFlow Database Setup Script
-- Run this in your PostgreSQL database to create all required tables

-- Drop existing tables if they exist (be careful with this in production!)
-- DROP TABLE IF EXISTS submissions CASCADE;
-- DROP TABLE IF EXISTS questions CASCADE;
-- DROP TABLE IF EXISTS quizzes CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create quizzes table
CREATE TABLE IF NOT EXISTS quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time_limit INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create questions table
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'multiple_choice',
    options JSON,
    correct_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    quiz_id INTEGER REFERENCES quizzes(id),
    answers JSON,
    score DECIMAL(5,2),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample quiz data
INSERT INTO quizzes (title, description, time_limit) VALUES 
    ('Sample Quiz', 'A sample quiz to test the system', 15)
ON CONFLICT DO NOTHING;

-- Get the quiz ID for inserting questions
DO $$
DECLARE
    quiz_id INTEGER;
BEGIN
    SELECT id INTO quiz_id FROM quizzes WHERE title = 'Sample Quiz' LIMIT 1;
    
    -- Insert sample questions
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (quiz_id, 'What is the capital of France?', 'multiple_choice', '["Paris", "London", "Berlin", "Madrid"]', 'Paris'),
        (quiz_id, 'What is 2 + 2?', 'multiple_choice', '["3", "4", "5", "6"]', '4'),
        (quiz_id, 'Explain the concept of gravity.', 'written', '[]', 'Gravity is a fundamental force that attracts objects with mass towards each other.')
    ON CONFLICT DO NOTHING;
END $$;

-- Display table info
SELECT 'Users table created' as status;
SELECT 'Quizzes table created' as status;
SELECT 'Questions table created' as status;
SELECT 'Submissions table created' as status;
SELECT 'Sample data inserted' as status;

-- Show sample data
SELECT 'Sample Quiz Data:' as info;
SELECT q.title, q.description, COUNT(qs.id) as question_count 
FROM quizzes q 
LEFT JOIN questions qs ON q.id = qs.quiz_id 
GROUP BY q.id, q.title, q.description;
