from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
from urllib.parse import parse_qs, urlparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        # Handle admin GET endpoints - simplified routing for Vercel
        if 'quizzes' in path:
            self.handle_get_quizzes()
        elif 'students' in path:
            self.handle_get_students()
        else:
            self.handle_get_quizzes()  # Default to quizzes
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Handle admin POST endpoints - simplified routing for Vercel
        if 'login' in path:
            self.handle_admin_login()
        elif 'quiz' in path and 'question' not in path:
            self.handle_create_quiz()
        elif 'question' in path:
            self.handle_create_question()
        elif 'broadcast' in path:
            self.handle_broadcast_email()
        else:
            self.handle_admin_login()  # Default to login
    
    def do_DELETE(self):
        path = urlparse(self.path).path
        
        if path.startswith('/api/admin/quiz/'):
            quiz_id = path.split('/')[-1]
            self.handle_delete_quiz(quiz_id)
        elif path.startswith('/api/admin/question/'):
            question_id = path.split('/')[-1]
            self.handle_delete_question(question_id)
        else:
            self.send_error(404)
    
    def handle_admin_login(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            password = data.get('password', '')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            
            if password == admin_password:
                self.send_json_response({'success': True, 'message': 'Admin login successful'})
            else:
                self.send_json_response({'success': False, 'message': 'Invalid admin password'})
                
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_get_quizzes(self):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT q.id, q.title, q.description, q.time_limit, COUNT(qs.id) as question_count
                FROM quizzes q
                LEFT JOIN questions qs ON q.id = qs.quiz_id
                GROUP BY q.id, q.title, q.description, q.time_limit
                ORDER BY q.id
            """)
            
            quizzes = []
            for row in cursor.fetchall():
                quizzes.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'time_limit': row[3],
                    'question_count': row[4]
                })
            
            self.send_json_response({'success': True, 'quizzes': quizzes})
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_get_students(self):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.name, u.email, u.created_at,
                       COUNT(s.id) as quiz_count,
                       AVG(s.score) as avg_score
                FROM users u
                LEFT JOIN submissions s ON u.id = s.user_id
                GROUP BY u.id, u.name, u.email, u.created_at
                ORDER BY u.created_at DESC
            """)
            
            students = []
            for row in cursor.fetchall():
                students.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'quiz_count': row[4] or 0,
                    'avg_score': float(row[5]) if row[5] else 0
                })
            
            self.send_json_response({'success': True, 'students': students})
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_create_quiz(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            time_limit = data.get('time_limit', 30)
            
            if not title:
                self.send_json_response({'success': False, 'message': 'Quiz title is required'})
                return
            
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO quizzes (title, description, time_limit)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (title, description, time_limit))
            
            quiz_id = cursor.fetchone()[0]
            conn.commit()
            
            self.send_json_response({
                'success': True, 
                'message': 'Quiz created successfully',
                'quiz_id': quiz_id
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_create_question(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            quiz_id = data.get('quiz_id')
            question_text = data.get('question_text', '').strip()
            question_type = data.get('question_type', 'multiple_choice')
            options = data.get('options', [])
            correct_answer = data.get('correct_answer', '').strip()
            
            if not all([quiz_id, question_text, correct_answer]):
                self.send_json_response({'success': False, 'message': 'All fields are required'})
                return
            
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO questions (quiz_id, question_text, question_type, options, correct_answer)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (quiz_id, question_text, question_type, json.dumps(options), correct_answer))
            
            question_id = cursor.fetchone()[0]
            conn.commit()
            
            self.send_json_response({
                'success': True, 
                'message': 'Question created successfully',
                'question_id': question_id
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_delete_quiz(self, quiz_id):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            # Delete questions first (foreign key constraint)
            cursor.execute("DELETE FROM questions WHERE quiz_id = %s", (quiz_id,))
            
            # Delete quiz
            cursor.execute("DELETE FROM quizzes WHERE id = %s", (quiz_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                self.send_json_response({'success': True, 'message': 'Quiz deleted successfully'})
            else:
                self.send_json_response({'success': False, 'message': 'Quiz not found'})
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_delete_question(self, question_id):
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                self.send_json_response({'success': True, 'message': 'Question deleted successfully'})
            else:
                self.send_json_response({'success': False, 'message': 'Question not found'})
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_broadcast_email(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            subject = data.get('subject', '').strip()
            message = data.get('message', '').strip()
            
            if not all([subject, message]):
                self.send_json_response({'success': False, 'message': 'Subject and message are required'})
                return
            
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            # Get all student emails
            cursor.execute("SELECT name, email FROM users")
            students = cursor.fetchall()
            
            if not students:
                self.send_json_response({'success': False, 'message': 'No students found'})
                return
            
            # Send emails
            gmail_user = os.getenv('GMAIL_USER')
            gmail_password = os.getenv('GMAIL_PASSWORD')
            
            if not gmail_user or not gmail_password:
                self.send_json_response({'success': False, 'message': 'Email configuration missing'})
                return
            
            sent_count = 0
            for name, email in students:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = gmail_user
                    msg['To'] = email
                    msg['Subject'] = subject
                    
                    body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0;">
                            <h1 style="margin: 0; font-size: 24px;">📢 QuizFlow Announcement</h1>
                        </div>
                        
                        <div style="padding: 30px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                            <h2 style="color: #1e293b;">Hello {name}! 👋</h2>
                            <div style="background: white; padding: 25px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                {message.replace(chr(10), '<br>')}
                            </div>
                            
                            <hr style="margin: 30px 0; border: none; height: 1px; background: #e2e8f0;">
                            <p style="font-size: 12px; color: #64748b; text-align: center;">
                                This message was sent from QuizFlow Administration. 🚀
                            </p>
                        </div>
                    </body>
                    </html>
                    """
                    
                    msg.attach(MIMEText(body, 'html'))
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(gmail_user, gmail_password)
                    text = msg.as_string()
                    server.sendmail(gmail_user, email, text)
                    server.quit()
                    
                    sent_count += 1
                    
                except Exception as e:
                    print(f"Failed to send email to {email}: {e}")
            
            self.send_json_response({
                'success': True, 
                'message': f'Broadcast sent to {sent_count} students'
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
