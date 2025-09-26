-- QuizFlow Test Data Setup
-- Run this script in your PostgreSQL database to add sample quizzes for testing

-- Insert sample quizzes
INSERT INTO quizzes (title, description, time_limit) VALUES 
    ('JavaScript Fundamentals', 'Test your knowledge of JavaScript basics and core concepts', 15),
    ('Web Development Quiz', 'Questions about HTML, CSS, and modern web development practices', 20),
    ('Programming Logic', 'Algorithmic thinking and problem-solving questions', 25)
ON CONFLICT DO NOTHING;

-- Get the quiz IDs for inserting questions
DO $$
DECLARE
    js_quiz_id INTEGER;
    web_quiz_id INTEGER;
    logic_quiz_id INTEGER;
BEGIN
    -- Get quiz IDs
    SELECT id INTO js_quiz_id FROM quizzes WHERE title = 'JavaScript Fundamentals' LIMIT 1;
    SELECT id INTO web_quiz_id FROM quizzes WHERE title = 'Web Development Quiz' LIMIT 1;
    SELECT id INTO logic_quiz_id FROM quizzes WHERE title = 'Programming Logic' LIMIT 1;
    
    -- JavaScript Fundamentals Questions
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (js_quiz_id, 'What is the correct way to declare a variable in JavaScript?', 'multiple_choice', 
         '["var myVar;", "variable myVar;", "v myVar;", "declare myVar;"]', 'var myVar;'),
        
        (js_quiz_id, 'Which method is used to add an element to the end of an array?', 'multiple_choice',
         '["push()", "pop()", "shift()", "unshift()"]', 'push()'),
        
        (js_quiz_id, 'What does "=== " operator do in JavaScript?', 'multiple_choice',
         '["Assignment", "Comparison without type checking", "Strict equality comparison", "Not equal"]', 'Strict equality comparison'),
        
        (js_quiz_id, 'Explain the difference between "let" and "var" in JavaScript.', 'written', '[]',
         'let has block scope while var has function scope. let variables cannot be redeclared in the same scope, while var can be. let variables are not hoisted to the top of their scope like var variables.'),
        
        (js_quiz_id, 'What will console.log(typeof null) output?', 'multiple_choice',
         '["null", "undefined", "object", "boolean"]', 'object');
    
    -- Web Development Quiz Questions
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (web_quiz_id, 'Which HTML tag is used to define an internal style sheet?', 'multiple_choice',
         '["<css>", "<script>", "<style>", "<link>"]', '<style>'),
        
        (web_quiz_id, 'What does CSS stand for?', 'multiple_choice',
         '["Creative Style Sheets", "Cascading Style Sheets", "Computer Style Sheets", "Colorful Style Sheets"]', 'Cascading Style Sheets'),
        
        (web_quiz_id, 'Which CSS property is used to change the text color?', 'multiple_choice',
         '["color", "text-color", "font-color", "text-style"]', 'color'),
        
        (web_quiz_id, 'Describe the purpose of responsive web design.', 'written', '[]',
         'Responsive web design ensures that web pages render well on different devices and screen sizes. It uses flexible layouts, images, and CSS media queries to provide an optimal viewing experience across desktops, tablets, and mobile devices.'),
        
        (web_quiz_id, 'What is the purpose of the alt attribute in HTML images?', 'multiple_choice',
         '["To make images load faster", "To provide alternative text for screen readers", "To add a border to images", "To resize images"]', 'To provide alternative text for screen readers');
    
    -- Programming Logic Questions
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (logic_quiz_id, 'What is the time complexity of binary search?', 'multiple_choice',
         '["O(n)", "O(log n)", "O(n²)", "O(1)"]', 'O(log n)'),
        
        (logic_quiz_id, 'Which data structure uses LIFO (Last In, First Out)?', 'multiple_choice',
         '["Queue", "Stack", "Array", "Linked List"]', 'Stack'),
        
        (logic_quiz_id, 'What is recursion in programming?', 'multiple_choice',
         '["A loop that never ends", "A function that calls itself", "A way to sort arrays", "A type of variable"]', 'A function that calls itself'),
        
        (logic_quiz_id, 'Explain the difference between an algorithm and a data structure.', 'written', '[]',
         'An algorithm is a step-by-step procedure or set of instructions to solve a problem, while a data structure is a way of organizing and storing data in memory. Algorithms operate on data structures to perform computations and solve problems efficiently.'),
        
        (logic_quiz_id, 'In a sorted array of 1000 elements, what is the maximum number of comparisons needed for binary search?', 'multiple_choice',
         '["10", "100", "500", "1000"]', '10');
    
    RAISE NOTICE 'Test quizzes created successfully!';
    RAISE NOTICE 'JavaScript Fundamentals Quiz ID: %', js_quiz_id;
    RAISE NOTICE 'Web Development Quiz ID: %', web_quiz_id;
    RAISE NOTICE 'Programming Logic Quiz ID: %', logic_quiz_id;
END $$;

-- Display the created quizzes and their questions
SELECT 'CREATED QUIZZES:' as info;
SELECT 
    q.id,
    q.title,
    q.description,
    q.time_limit,
    COUNT(qs.id) as question_count
FROM quizzes q
LEFT JOIN questions qs ON q.id = qs.quiz_id
GROUP BY q.id, q.title, q.description, q.time_limit
ORDER BY q.id;

SELECT 'SAMPLE QUESTIONS:' as info;
SELECT 
    q.title as quiz_title,
    qs.question_text,
    qs.question_type,
    CASE 
        WHEN qs.question_type = 'multiple_choice' THEN qs.options::text
        ELSE 'Written Answer'
    END as options
FROM quizzes q
JOIN questions qs ON q.id = qs.quiz_id
ORDER BY q.id, qs.id
LIMIT 10;
