# 🚀 QuizFlow: Professional Quiz Platform ✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-000?logo=vercel)](https://vercel.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue?logo=postgresql)](https://postgresql.org)

**QuizFlow** is a modern, professional quiz platform designed for educational institutions and corporate training. Built with a **serverless architecture** on Vercel, featuring a sleek modern UI, comprehensive admin management, and automated email notifications.

Experience seamless quiz delivery with real-time scoring, detailed analytics, and a mobile-responsive design that works perfectly across all devices.

---

## ✨ Key Features

### 🎓 **Student Experience**
* **Modern Professional UI** - Dark theme with glassmorphism effects and smooth animations
* **Interactive Quiz Taking** - Multiple choice and written questions with auto-save
* **Advanced Navigation** - Question overview panel, jump to any question, progress tracking
* **Rich Text Editor** - For written answers with formatting tools and keyboard shortcuts
* **Real-time Timer** - Visual countdown with automatic submission when time expires
* **Instant Results** - Immediate scoring with detailed performance breakdown
* **Email Notifications** - Welcome emails and comprehensive result reports

### 👨‍💼 **Admin Management**
* **Complete Quiz Builder** - Create and manage quizzes with drag-and-drop simplicity
* **Question Bank Management** - Support for multiple question types and bulk operations
* **Student Analytics** - Real-time performance tracking and detailed progress reports
* **Email Broadcasting** - Send announcements and updates to all students
* **User Management** - Monitor student registrations and quiz attempts
* **Dashboard Overview** - Key metrics and system health at a glance

### 🔧 **Technical Excellence**
* **Serverless Architecture** - Built for Vercel with automatic scaling
* **PostgreSQL Database** - Reliable cloud database with optimized queries
* **Email Integration** - Professional HTML emails via Gmail SMTP
* **Mobile Responsive** - Perfect experience on desktop, tablet, and mobile
* **Security First** - Access codes, admin authentication, and secure data handling
* **Performance Optimized** - Fast loading times and smooth interactions

---

## 🏗️ Architecture

```
QuizFlow (Serverless)
├── Frontend (Static Files)
│   ├── index.html         # Student quiz interface
│   ├── admin.html         # Admin management panel  
│   └── login.html         # Authentication page
├── API (Serverless Functions)
│   ├── auth.py           # User authentication & registration
│   ├── quiz.py           # Quiz delivery & submissions
│   └── admin.py          # Admin management functions
├── Configuration
│   ├── vercel.json       # Vercel deployment config
│   └── requirements.txt  # Python dependencies
├── Database
│   ├── database_setup.sql    # Complete database schema
│   ├── database_migration.sql # Migration for existing databases
│   ├── sample_data.sql       # Basic sample data
│   └── test_quiz_data.sql    # Comprehensive test quizzes
└── Documentation
    ├── README.md         # This file
    └── VERCEL_DEPLOYMENT.md  # Detailed deployment guide
```

---

## 🚀 Quick Deploy to Vercel

### One-Click Deployment
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/rehmanpranto/QuizFlow)

### Manual Deployment Steps

1. **Fork/Clone the Repository**
   ```bash
   git clone https://github.com/rehmanpranto/QuizFlow.git
   cd QuizFlow
   ```

2. **Deploy to Vercel**
   - Go to [vercel.com](https://vercel.com) and sign in
   - Click "New Project" → Import your GitHub repository
   - Vercel automatically detects the configuration

3. **Configure Environment Variables**
   In your Vercel dashboard, go to Settings → Environment Variables and add:
   
   | Variable Name | Value | Description |
   |---------------|-------|-------------|
   | `DATABASE_URL` | `postgresql://user:password@host:port/database` | Your PostgreSQL connection string |
   | `GMAIL_USER` | `your-email@gmail.com` | Gmail address for sending emails |
   | `GMAIL_PASSWORD` | `your-gmail-app-password` | Gmail app password (not regular password) |
   | `STUDENT_ACCESS_CODE` | `12345` | Access code for students |
   | `ADMIN_PASSWORD` | `admin123` | Admin panel password |

4. **Set Up Database**
   ```sql
   -- Create required tables (PostgreSQL)
   CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       email VARCHAR(255) UNIQUE NOT NULL,
       password VARCHAR(255) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE quizzes (
       id SERIAL PRIMARY KEY,
       title VARCHAR(255) NOT NULL,
       description TEXT,
       time_limit INTEGER DEFAULT 30,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE questions (
       id SERIAL PRIMARY KEY,
       quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
       question_text TEXT NOT NULL,
       question_type VARCHAR(50) DEFAULT 'multiple_choice',
       options JSON,
       correct_answer TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE submissions (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       quiz_id INTEGER REFERENCES quizzes(id),
       answers JSON,
       score DECIMAL(5,2),
       completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

5. **Add Sample Quiz Data** (Optional but recommended for testing)
   ```sql
   -- Run test_quiz_data.sql in your database to add sample quizzes
   -- This creates 3 test quizzes with multiple choice and written questions
   ```

6. **Gmail App Password Setup**
   - Enable 2FA on your Google account
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate app password for "Mail"
   - Use this password in `GMAIL_PASSWORD` environment variable

---

## 🔗 Live Demo & Access

- **Student Interface**: `your-domain.vercel.app`
- **Admin Panel**: `your-domain.vercel.app/admin`
- **Login Page**: `your-domain.vercel.app/login`

### Default Access Credentials
- **Student Access Code**: `12345`
- **Admin Password**: `admin123`

---

## 📱 API Endpoints

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

---

## 🛠️ Local Development

For local development, you can still run the original Flask application:

```bash
# Clone the repository
git clone https://github.com/rehmanpranto/QuizFlow.git
cd QuizFlow

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit .env with your credentials

# Run locally
python app.py
```

---

## 🔒 Security Features

- **Access Code Protection** - Students need valid codes to access quizzes
- **Admin Authentication** - Secure admin panel with password protection
- **SQL Injection Prevention** - Parameterized queries throughout
- **CORS Configuration** - Proper cross-origin request handling
- **Environment Variables** - Sensitive data stored securely

---

## 📧 Email Notifications

QuizFlow includes comprehensive email functionality:

- **Welcome Emails** - Sent when students first login
- **Result Emails** - Detailed performance reports after quiz completion
- **Admin Broadcasts** - Send announcements to all students
- **Professional Templates** - HTML emails with modern design

---

## 🎯 Screenshots

### Student Quiz Interface
![Student Interface](https://via.placeholder.com/800x400/1e293b/ffffff?text=Modern+Quiz+Interface)

### Admin Management Panel
![Admin Panel](https://via.placeholder.com/800x400/667eea/ffffff?text=Comprehensive+Admin+Dashboard)

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🆘 Support

For detailed deployment instructions, see [`VERCEL_DEPLOYMENT.md`](./VERCEL_DEPLOYMENT.md)

For issues and questions, please open a GitHub issue.

---

**Ready to revolutionize your quiz experience? Deploy QuizFlow today!** 🚀
