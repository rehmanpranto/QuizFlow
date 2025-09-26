# QuizFlow - Vercel Deployment Guide 🚀

## Overview
QuizFlow has been successfully converted to a serverless architecture compatible with Vercel deployment. The application now uses serverless functions instead of a traditional Flask server.

## Architecture Changes Made

### 1. Serverless Functions Created
- **`/api/auth.py`** - Handles user authentication and login
- **`/api/quiz.py`** - Manages quiz questions, submissions, and scoring
- **`/api/admin.py`** - Administrative functions for quiz management

### 2. Vercel Configuration
- **`vercel.json`** - Deployment configuration with routing rules
- **`/api/requirements.txt`** - Python dependencies for serverless functions

## Deployment Steps

### Step 1: Environment Variables
Set these environment variables in your Vercel dashboard:

```
DATABASE_URL=your_postgresql_connection_string
GMAIL_USER=your_gmail_address
GMAIL_PASSWORD=your_gmail_app_password
STUDENT_ACCESS_CODE=12345
ADMIN_PASSWORD=admin123
```

### Step 2: Database Setup
Ensure your PostgreSQL database (Neon or similar) has these tables:

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    access_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quizzes table
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    time_limit INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions table
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'multiple_choice',
    options JSON,
    correct_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Submissions table
CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    quiz_id INTEGER REFERENCES quizzes(id),
    answers JSON,
    score DECIMAL(5,2),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Step 3: Deploy to Vercel

1. **Connect Repository**
   ```bash
   # If not already done, push to GitHub
   git add .
   git commit -m "Convert to Vercel serverless architecture"
   git push origin main
   ```

2. **Deploy via Vercel Dashboard**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Vercel will automatically detect the configuration

3. **Deploy via Vercel CLI** (Alternative)
   ```bash
   npm i -g vercel
   vercel login
   vercel --prod
   ```

## API Endpoints

### Authentication
- `POST /api/auth` - User login and registration

### Quiz Management
- `GET /api/quiz/questions?quiz_id=1` - Get quiz questions
- `GET /api/quiz/list` - Get all available quizzes
- `POST /api/quiz/submit` - Submit quiz answers

### Admin Functions
- `POST /api/admin/login` - Admin authentication
- `GET /api/admin/quizzes` - Get all quizzes with stats
- `GET /api/admin/students` - Get student analytics
- `POST /api/admin/quiz` - Create new quiz
- `POST /api/admin/question` - Add question to quiz
- `DELETE /api/admin/quiz/{id}` - Delete quiz
- `DELETE /api/admin/question/{id}` - Delete question
- `POST /api/admin/broadcast` - Send email to all students

## Features Included

### Student Features ✨
- **Modern Professional UI** - Dark theme with glassmorphism effects
- **Quiz Navigation** - Question overview, jump to questions, progress tracking
- **Written Questions** - Rich text editor with formatting tools
- **Auto-save** - Automatic answer saving as you type
- **Email Notifications** - Welcome and completion emails
- **Responsive Design** - Works on all devices

### Admin Features 🛠️
- **Quiz Management** - Create, edit, delete quizzes
- **Question Bank** - Add multiple choice and written questions
- **Student Analytics** - View student performance and statistics
- **Email Broadcasting** - Send announcements to all students
- **Real-time Updates** - Live quiz and student data

### Technical Features 🔧
- **Serverless Architecture** - Scalable and cost-effective
- **PostgreSQL Database** - Reliable cloud database storage
- **Email Integration** - Gmail SMTP for notifications
- **Professional UI/UX** - Modern design with smooth animations
- **Security** - Access codes and admin authentication

## Post-Deployment

1. **Test All Features**
   - Student login and quiz taking
   - Admin panel functionality
   - Email notifications
   - Database operations

2. **Add Sample Data**
   - Create initial quizzes through admin panel
   - Test with sample questions

3. **Configure Domain** (Optional)
   - Set up custom domain in Vercel dashboard
   - Update any hardcoded URLs if needed

## Troubleshooting

### Common Issues:
1. **Database Connection** - Verify DATABASE_URL is correct
2. **Email Issues** - Check Gmail app password configuration
3. **CORS Errors** - Headers are configured in serverless functions
4. **Function Timeouts** - Optimize database queries if needed

### Monitoring:
- Check Vercel function logs for errors
- Monitor database connection limits
- Track email delivery rates

## Success! 🎉
Your QuizFlow application is now ready for production on Vercel with:
- Serverless architecture
- Professional UI/UX
- Email notifications
- Admin management
- Student analytics
- Mobile responsiveness

The application will automatically scale based on usage and provide a seamless experience for both students and administrators.
