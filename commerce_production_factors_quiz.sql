-- O Level Commerce - Production Factors Quiz (1 Hour Duration)
-- 4 sections × 15 minutes each = 60 minutes total
-- Mix of multiple choice (quick) and written questions (detailed)

INSERT INTO quizzes (title, description, time_limit) VALUES 
    ('O Level Commerce Production Factors', 'Complete 1-hour quiz on factors of production: Land, Labor, Capital, and Enterprise. Divided into 4 sections of 15 minutes each.', 60)
ON CONFLICT DO NOTHING;

DO $$
DECLARE
    quiz_id INTEGER;
BEGIN
    SELECT id INTO quiz_id FROM quizzes WHERE title = 'O Level Commerce Production Factors' LIMIT 1;
    
    -- SECTION A: LAND (Questions 1-7) - 15 minutes
    INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer) VALUES 
        -- Quick multiple choice (2-3 minutes each)
        (quiz_id, 'Land as a factor of production includes all of the following EXCEPT:', 'multiple_choice',
         '["Forests and minerals", "Rivers and lakes", "Factory buildings", "Agricultural soil"]', 'Factory buildings'),
        
        (quiz_id, 'The economic reward for land is:', 'multiple_choice',
         '["Wages", "Profit", "Interest", "Rent"]', 'Rent'),
        
        (quiz_id, 'Which statement about land is TRUE?', 'multiple_choice',
         '["Land supply can be increased easily", "Land is perfectly mobile", "Land is a free gift of nature", "All land has the same productivity"]', 'Land is a free gift of nature'),
        
        (quiz_id, 'The fertility of land can be improved by:', 'multiple_choice',
         '["Using fertilizers", "Proper irrigation", "Crop rotation", "All of the above"]', 'All of the above'),
        
        -- Written question (7-8 minutes)
        (quiz_id, 'Explain THREE characteristics of land as a factor of production and discuss how the location of land affects its economic value.', 'written', '[]',
         'Three characteristics: 1) Limited supply - land cannot be manufactured or increased beyond natural limits, 2) Immobility - land cannot be moved from one place to another, 3) Varying productivity - different plots have different fertility and natural resources. Location affects value through: proximity to markets (reducing transport costs), access to infrastructure (roads, utilities), climate suitability for specific crops, and potential for urban development. Prime locations command higher rent due to better economic opportunities.'),

    -- SECTION B: LABOR (Questions 8-14) - 15 minutes  
        (quiz_id, 'The reward for labor in production is:', 'multiple_choice',
         '["Rent", "Interest", "Wages and salaries", "Dividend"]', 'Wages and salaries'),
        
        (quiz_id, 'Division of labor means:', 'multiple_choice',
         '["Separating workers by gender", "Breaking production into specialized tasks", "Working in different shifts", "Paying different wages"]', 'Breaking production into specialized tasks'),
        
        (quiz_id, 'Which factor does NOT affect labor productivity?', 'multiple_choice',
         '["Training and education", "Working conditions", "The color of factory walls", "Health and nutrition"]', 'The color of factory walls'),
        
        (quiz_id, 'Occupational mobility of labor refers to:', 'multiple_choice',
         '["Moving between different jobs", "Moving between locations", "Working overtime", "Changing salary levels"]', 'Moving between different jobs'),
        
        -- Written question (7-8 minutes)
        (quiz_id, 'Analyze FOUR advantages and TWO disadvantages of division of labor in modern manufacturing. Give a practical example.', 'written', '[]',
         'Advantages: 1) Increased efficiency - workers become experts in specific tasks, 2) Higher output - specialization leads to faster production, 3) Cost reduction - less time wasted switching between tasks, 4) Innovation - focused workers can suggest improvements. Disadvantages: 1) Monotony - repetitive work reduces job satisfaction, 2) Interdependence - breakdown in one area stops entire production. Example: Car assembly line where each worker specializes in installing specific parts, resulting in efficient mass production but creating boring, repetitive jobs.'),

    -- SECTION C: CAPITAL (Questions 15-21) - 15 minutes
        (quiz_id, 'Capital as a factor of production includes:', 'multiple_choice',
         '["Money in the bank only", "Machinery and equipment only", "All man-made aids to production", "Natural resources only"]', 'All man-made aids to production'),
        
        (quiz_id, 'The difference between fixed and working capital is:', 'multiple_choice',
         '["Fixed capital is more expensive", "Fixed capital lasts longer in production", "Working capital earns more profit", "There is no difference"]', 'Fixed capital lasts longer in production'),
        
        (quiz_id, 'Which is an example of working capital?', 'multiple_choice',
         '["Factory building", "Raw materials inventory", "Delivery trucks", "Computer systems"]', 'Raw materials inventory'),
        
        (quiz_id, 'Capital formation occurs through:', 'multiple_choice',
         '["Consumption", "Saving and investment", "Borrowing only", "Government spending only"]', 'Saving and investment'),
        
        -- Written question (7-8 minutes)
        (quiz_id, 'Distinguish between fixed capital and working capital. Explain how capital formation contributes to economic growth with examples.', 'written', '[]',
         'Fixed capital consists of durable assets used repeatedly over long periods (machinery, buildings, equipment), while working capital includes current assets consumed in production (raw materials, cash, inventory). Capital formation through saving and investment drives economic growth by: 1) Increasing productive capacity - new factories create more output, 2) Improving efficiency - modern machinery reduces costs, 3) Creating employment - new businesses hire workers, 4) Generating innovation - investment in R&D develops new technologies. Example: Investment in automated textile machinery (fixed capital) increases cloth production while requiring cotton supplies (working capital).'),

    -- SECTION D: ENTERPRISE/ENTREPRENEUR (Questions 22-28) - 15 minutes
        (quiz_id, 'The entrepreneur''s reward is:', 'multiple_choice',
         '["Fixed salary", "Profit", "Commission", "Interest"]', 'Profit'),
        
        (quiz_id, 'The main function of an entrepreneur is:', 'multiple_choice',
         '["To provide capital", "To work manually", "To organize and coordinate other factors", "To own land"]', 'To organize and coordinate other factors'),
        
        (quiz_id, 'Entrepreneurs take risks because they:', 'multiple_choice',
         '["Enjoy uncertainty", "Want to earn profit", "Have excess money", "Are forced by government"]', 'Want to earn profit'),
        
        (quiz_id, 'Which quality is MOST important for an entrepreneur?', 'multiple_choice',
         '["Risk-taking ability", "Physical strength", "Government connections", "Family wealth"]', 'Risk-taking ability'),
        
        -- Final comprehensive written question (7-8 minutes)
        (quiz_id, 'Explain the role of the entrepreneur in combining the factors of production. Discuss FIVE qualities of a successful entrepreneur and explain why each is essential for business success.', 'written', '[]',
         'Entrepreneurs coordinate land, labor, and capital to create goods and services profitably. Essential qualities: 1) Risk-taking - businesses face uncertainty and potential losses, requiring courage to invest, 2) Leadership - entrepreneurs must motivate employees and make decisive choices, 3) Innovation - creating new products or methods gives competitive advantage, 4) Organizational skills - efficiently combining resources maximizes productivity, 5) Perseverance - overcoming obstacles and failures is crucial for long-term success. These qualities enable entrepreneurs to identify opportunities, mobilize resources, and create value while bearing business risks for potential profits.');

    RAISE NOTICE 'O Level Commerce Production Factors Quiz Created!';
    RAISE NOTICE 'Duration: 1 hour (60 minutes)';
    RAISE NOTICE 'Structure: 4 sections × 15 minutes each';
    RAISE NOTICE 'Total Questions: 28 (21 multiple choice + 7 written)';
    RAISE NOTICE 'Coverage: Land, Labor, Capital, Enterprise';
END $$;
