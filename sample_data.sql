-- Quick setup for QuizFlow - Insert sample quiz if none exists

-- Insert a sample quiz if the table is empty
INSERT INTO quizzes (title, description, time_limit) 
SELECT 'Sample Quiz', 'Welcome to QuizFlow! This is a sample quiz to get you started.', 10
WHERE NOT EXISTS (SELECT 1 FROM quizzes);

-- Get the quiz ID (will be 1 if it's the first quiz)
DO $$
DECLARE
    quiz_id INTEGER;
BEGIN
    SELECT id INTO quiz_id FROM quizzes ORDER BY id LIMIT 1;
    
    -- Insert sample questions for the quiz
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (quiz_id, 'What is the capital of France?', 'multiple_choice', '["Paris", "London", "Berlin", "Madrid"]', 'Paris'),
        (quiz_id, 'What is 2 + 2?', 'multiple_choice', '["3", "4", "5", "6"]', '4'),
        (quiz_id, 'What programming language is used for web development?', 'multiple_choice', '["Python", "JavaScript", "Java", "C++"]', 'JavaScript')
    ON CONFLICT DO NOTHING;
    
    RAISE NOTICE 'Sample quiz created with ID: %', quiz_id;
END $$;

-- Verify the data
SELECT 'Quizzes in database:' as info;
SELECT id, title, description FROM quizzes;

SELECT 'Questions in database:' as info;
SELECT q.title, qs.question_text 
FROM quizzes q 
JOIN questions qs ON q.id = qs.quiz_id 
ORDER BY q.id, qs.id;
