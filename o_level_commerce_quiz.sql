-- O Level Commerce Quiz Template
-- Customize this with your actual questions from the PDF

-- Insert the main quiz
INSERT INTO quizzes (title, description, time_limit) VALUES 
    ('O Level Commerce - Production Factors', 'Comprehensive quiz on production factors covering land, labor, capital, and enterprise', 60)
ON CONFLICT DO NOTHING;

-- Get the quiz ID for inserting questions
DO $$
DECLARE
    commerce_quiz_id INTEGER;
BEGIN
    SELECT id INTO commerce_quiz_id FROM quizzes WHERE title = 'O Level Commerce - Production Factors' LIMIT 1;
    
    -- Section 1: Land as a Factor of Production (15 minutes worth)
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (commerce_quiz_id, 'Which of the following is considered a natural resource in production?', 'multiple_choice',
         '["Machinery", "Land", "Factory buildings", "Computer software"]', 'Land'),
        
        (commerce_quiz_id, 'What is the reward for land as a factor of production?', 'multiple_choice',
         '["Wages", "Profit", "Rent", "Interest"]', 'Rent'),
        
        (commerce_quiz_id, 'Which characteristic makes land different from other factors of production?', 'multiple_choice',
         '["It can be moved", "It has unlimited supply", "It is a free gift of nature", "It can be manufactured"]', 'It is a free gift of nature'),
        
        (commerce_quiz_id, 'Explain the importance of land in agricultural production and give two examples of how land quality affects productivity.', 'written', '[]',
         'Land is crucial for agriculture as it provides the natural foundation for crop growth. Fertile soil with good drainage increases crop yields, while poor soil quality or unsuitable climate conditions can significantly reduce productivity. Examples include: 1) Rich alluvial soil producing higher grain yields than sandy soil, 2) Land with adequate rainfall supporting better crop growth than drought-prone areas.'),
        
        (commerce_quiz_id, 'What is meant by the mobility of land?', 'multiple_choice',
         '["Land can be easily transported", "Land is geographically immobile", "Land can change its nature", "Land can be bought and sold"]', 'Land is geographically immobile');
    
    -- Section 2: Labor as a Factor of Production (15 minutes worth)
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (commerce_quiz_id, 'What is the reward for labor in production?', 'multiple_choice',
         '["Rent", "Interest", "Wages", "Profit"]', 'Wages'),
        
        (commerce_quiz_id, 'Which of the following improves the efficiency of labor?', 'multiple_choice',
         '["Training and education", "Longer working hours", "Reducing wages", "Increasing supervision"]', 'Training and education'),
        
        (commerce_quiz_id, 'What is division of labor?', 'multiple_choice',
         '["Sharing profits among workers", "Breaking work into specialized tasks", "Working in different locations", "Competing between workers"]', 'Breaking work into specialized tasks'),
        
        (commerce_quiz_id, 'Discuss three advantages and two disadvantages of division of labor in modern production.', 'written', '[]',
         'Advantages: 1) Increased efficiency through specialization, 2) Higher productivity as workers become skilled in specific tasks, 3) Time saving as workers don''t switch between different activities. Disadvantages: 1) Monotony and boredom from repetitive work, 2) Interdependence where breakdown in one area affects the entire production process.'),
        
        (commerce_quiz_id, 'Which factor affects the supply of labor?', 'multiple_choice',
         '["Population size", "Weather conditions", "Interest rates", "Land availability"]', 'Population size');
    
    -- Section 3: Capital as a Factor of Production (15 minutes worth)
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (commerce_quiz_id, 'What is the reward for capital in production?', 'multiple_choice',
         '["Wages", "Profit", "Rent", "Interest"]', 'Interest'),
        
        (commerce_quiz_id, 'Which of the following is an example of fixed capital?', 'multiple_choice',
         '["Raw materials", "Money in bank", "Factory building", "Finished goods"]', 'Factory building'),
        
        (commerce_quiz_id, 'What is working capital?', 'multiple_choice',
         '["Money used to buy machinery", "Capital used in day-to-day operations", "Profit from business", "Loans from banks"]', 'Capital used in day-to-day operations'),
        
        (commerce_quiz_id, 'Explain the difference between fixed capital and working capital with examples.', 'written', '[]',
         'Fixed capital refers to durable assets used repeatedly in production over a long period, such as machinery, buildings, and equipment. Working capital consists of current assets used up in the production process, including raw materials, cash, and inventory. Example: A bakery''s ovens and building are fixed capital, while flour, sugar, and daily cash for operations are working capital.'),
        
        (commerce_quiz_id, 'How is capital formed in an economy?', 'multiple_choice',
         '["Through consumption", "Through saving and investment", "Through borrowing only", "Through government grants"]', 'Through saving and investment');
    
    -- Section 4: Enterprise/Entrepreneur (15 minutes worth)
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        (commerce_quiz_id, 'What is the reward for entrepreneurship?', 'multiple_choice',
         '["Wages", "Interest", "Rent", "Profit"]', 'Profit'),
        
        (commerce_quiz_id, 'Which is the primary function of an entrepreneur?', 'multiple_choice',
         '["Providing labor", "Risk-taking and decision making", "Providing land", "Lending money"]', 'Risk-taking and decision making'),
        
        (commerce_quiz_id, 'An entrepreneur combines other factors of production to create:', 'multiple_choice',
         '["More land", "More labor", "Goods and services", "More capital"]', 'Goods and services'),
        
        (commerce_quiz_id, 'Describe four qualities of a successful entrepreneur and explain why each is important.', 'written', '[]',
         'Four important qualities: 1) Risk-taking ability - essential for starting new ventures and making bold decisions, 2) Leadership skills - needed to motivate and guide employees effectively, 3) Innovation and creativity - helps develop new products and find better ways of doing things, 4) Decision-making skills - crucial for making quick and effective choices in business situations. These qualities enable entrepreneurs to successfully combine other factors of production and create value.'),
        
        (commerce_quiz_id, 'What type of risk does an entrepreneur face?', 'multiple_choice',
         '["No risk", "Only financial risk", "Business and financial risks", "Only reputation risk"]', 'Business and financial risks');

    RAISE NOTICE 'O Level Commerce Quiz created successfully!';
    RAISE NOTICE 'Quiz ID: %', commerce_quiz_id;
    RAISE NOTICE 'Total Questions: 20 (5 per section, designed for 1-hour duration)';
END $$;

-- Verify the quiz was created
SELECT 
    q.title,
    q.description,
    q.time_limit,
    COUNT(qs.id) as question_count
FROM quizzes q
LEFT JOIN questions qs ON q.id = qs.quiz_id
WHERE q.title = 'O Level Commerce - Production Factors'
GROUP BY q.id, q.title, q.description, q.time_limit;
