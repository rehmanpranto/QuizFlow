from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
from urllib.parse import parse_qs, urlparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in production, which is fine

class handler(BaseHTTPRequestHandler):
    def _connect_db(self):
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception('Database not configured')
        kwargs = {}
        if 'sslmode=' not in database_url.lower():
            kwargs['sslmode'] = 'require'
        return psycopg2.connect(database_url, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        
        # Handle admin GET endpoints - check the specific endpoint
        if path.startswith('/quiz/') and path.endswith('/questions'):
            # Expecting /quiz/{id}/questions
            try:
                parts = path.strip('/').split('/')
                quiz_id = parts[1]
            except Exception:
                return self.send_json_response({'success': False, 'message': 'Invalid path'})
            return self.handle_get_questions_for_quiz(quiz_id)
        elif '/quizzes' in path:
            self.handle_get_quizzes()
        elif '/students' in path:
            self.handle_get_students()
        else:
            self.handle_get_quizzes()  # Default to quizzes
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Handle admin POST endpoints - check the specific endpoint
        if '/login' in path:
            self.handle_admin_login()
        elif path.startswith('/quiz/') and path.endswith('/question'):
            # Expecting /quiz/{id}/question from UI, merge id into payload
            try:
                parts = path.strip('/').split('/')
                quiz_id = int(parts[1])
            except Exception:
                return self.send_json_response({'success': False, 'message': 'Invalid quiz id in path'})
            self.handle_create_question(quiz_id_from_path=quiz_id)
        elif '/quiz' in path and '/question' not in path:
            self.handle_create_quiz()
        elif '/broadcast' in path:
            self.handle_broadcast_email()
        else:
            self.handle_admin_login()  # Default to login
    
    def do_DELETE(self):
        path = urlparse(self.path).path
        
        # Debug logging
        print(f"DEBUG DELETE: Full path: {self.path}")
        print(f"DEBUG DELETE: Parsed path: {path}")
        
        # Handle different path formats - with or without /api/admin prefix
        if '/quiz/' in path and '/question' not in path:
            # Extract quiz ID from path like /api/admin/quiz/123 or /quiz/123
            parts = path.split('/')
            quiz_id = None
            for i, part in enumerate(parts):
                if part == 'quiz' and i + 1 < len(parts):
                    quiz_id = parts[i + 1]
                    break
            
            if quiz_id:
                print(f"DEBUG DELETE: Extracted quiz_id: {quiz_id}")
                self.handle_delete_quiz(quiz_id)
            else:
                print("DEBUG DELETE: Could not extract quiz_id")
                self.send_json_response({'success': False, 'message': 'Invalid quiz ID in path'})
                
        elif '/question/' in path:
            # Extract question ID from path like /api/admin/question/123 or /question/123
            parts = path.split('/')
            question_id = None
            for i, part in enumerate(parts):
                if part == 'question' and i + 1 < len(parts):
                    question_id = parts[i + 1]
                    break
            
            if question_id:
                print(f"DEBUG DELETE: Extracted question_id: {question_id}")
                self.handle_delete_question(question_id)
            else:
                print("DEBUG DELETE: Could not extract question_id")
                self.send_json_response({'success': False, 'message': 'Invalid question ID in path'})
        else:
            print(f"DEBUG DELETE: No matching route for path: {path}")
            self.send_json_response({'success': False, 'message': 'DELETE endpoint not found'})
    
    def handle_admin_login(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            password = data.get('password', '')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            
            # Debug logging (remove in production)
            print(f"DEBUG: Received password: '{password}'")
            print(f"DEBUG: Expected password: '{admin_password}'")
            print(f"DEBUG: Passwords match: {password == admin_password}")
            
            if password == admin_password:
                self.send_json_response({'success': True, 'message': 'Admin login successful'})
            else:
                self.send_json_response({'success': False, 'message': 'Invalid admin password'})
                
        except Exception as e:
            print(f"DEBUG: Login error: {e}")
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_get_quizzes(self):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT q.id, q.title, q.description, q.time_limit, q.created_at, COUNT(qs.id) as question_count
                FROM quizzes q
                LEFT JOIN questions qs ON q.id = qs.quiz_id
                GROUP BY q.id, q.title, q.description, q.time_limit, q.created_at
                ORDER BY q.id
            """)
            
            quizzes = []
            for row in cursor.fetchall():
                quizzes.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'timePerQuestion': row[3],  # reuse time_limit for display
                    'createdAt': row[4].isoformat() if row[4] else None,
                    'questionCount': row[5],
                    'isActive': True  # no status column; default to active
                })
            
            self.send_json_response({'success': True, 'quizzes': quizzes})
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_get_students(self):
        try:
            conn = self._connect_db()
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
            # accept both time_limit and timeLimit
            time_limit = data.get('time_limit') or data.get('timeLimit') or 30
            
            if not title:
                self.send_json_response({'success': False, 'message': 'Quiz title is required'})
                return
            
            conn = self._connect_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO quizzes (title, description, time_limit)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (title, description, int(time_limit)))
            
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
    
    def handle_create_question(self, quiz_id_from_path=None):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Support admin UI payload shape
            quiz_id = quiz_id_from_path or data.get('quiz_id')
            question_text = (data.get('question_text') or data.get('questionText') or '').strip()
            question_type = data.get('question_type') or 'multiple_choice'
            
            # Handle options based on question type
            options = data.get('options')
            correct_answer = data.get('correct_answer')
            
            if question_type == 'essay':
                # For essay questions, options contain instructions and maxWords
                if not options:
                    options = {}
                # correct_answer should already be set for essay questions
            else:
                # For multiple choice questions - Options can come as optionA-D + correctAnswer index
                if not options:
                    optionA = data.get('optionA')
                    optionB = data.get('optionB')
                    optionC = data.get('optionC')
                    optionD = data.get('optionD')
                    options = [opt for opt in [optionA, optionB, optionC, optionD] if opt is not None]
                    
                if correct_answer is None and 'correctAnswer' in data:
                    idx = data.get('correctAnswer')
                    try:
                        idx = int(idx)
                        if isinstance(options, list) and 0 <= idx < len(options):
                            correct_answer = options[idx]
                    except Exception:
                        correct_answer = ''
            
            if not all([quiz_id, question_text, correct_answer]):
                self.send_json_response({'success': False, 'message': 'All fields are required'})
                return
            
            conn = self._connect_db()
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
    
    def handle_get_questions_for_quiz(self, quiz_id):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, question_text, question_type, options, correct_answer
                FROM questions
                WHERE quiz_id = %s
                ORDER BY id
                """,
                (quiz_id,)
            )
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                q_id, q_text, q_type, q_options, q_correct = row
                try:
                    opts = json.loads(q_options) if q_options else []
                except Exception:
                    opts = []
                
                question_data = {
                    'id': q_id,
                    'questionText': q_text,
                    'questionType': q_type or 'multiple_choice',
                    'correctAnswer': q_correct
                }
                
                if q_type == 'essay':
                    # For essay questions, options contains instructions and metadata
                    question_data['options'] = opts if isinstance(opts, dict) else {}
                    # correctAnswer contains the sample answer for essays
                else:
                    # For multiple choice questions - Map to admin UI shape
                    correct_index = -1
                    if isinstance(opts, list) and q_correct in opts:
                        correct_index = opts.index(q_correct)
                    question_data.update({
                        'optionA': opts[0] if len(opts) > 0 else '',
                        'optionB': opts[1] if len(opts) > 1 else '',
                        'optionC': opts[2] if len(opts) > 2 else '',
                        'optionD': opts[3] if len(opts) > 3 else '',
                        'correctAnswer': correct_index,
                        'options': opts
                    })
                
                questions.append(question_data)
            
            self.send_json_response({'success': True, 'questions': questions})
            cursor.close()
            conn.close()
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_delete_quiz(self, quiz_id):
        try:
            # Validate quiz_id
            try:
                quiz_id = int(quiz_id)
            except (ValueError, TypeError):
                self.send_json_response({'success': False, 'message': 'Invalid quiz ID format'})
                return
                
            print(f"DEBUG: Deleting quiz with ID: {quiz_id}")
            
            conn = self._connect_db()
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
            # Validate question_id
            try:
                question_id = int(question_id)
            except (ValueError, TypeError):
                self.send_json_response({'success': False, 'message': 'Invalid question ID format'})
                return
                
            print(f"DEBUG: Deleting question with ID: {question_id}")
            
            conn = self._connect_db()
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
            
            conn = self._connect_db()
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
                    <body style=\"font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;\">
                        <div style=\"background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0;\">
                            <h1 style=\"margin: 0; font-size: 24px;\">📢 QuizFlow Announcement</h1>
                        </div>
                        
                        <div style=\"padding: 30px; background: #f8fafc; border-radius: 0 0 10px 10px;\">
                            <h2 style=\"color: #1e293b;\">Hello {name}! 👋</h2>
                            <div style=\"background: white; padding: 25px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);\">
                                {message.replace(chr(10), '<br>')}
                            </div>
                            
                            <hr style=\"margin: 30px 0; border: none; height: 1px; background: #e2e8f0;\">
                            <p style=\"font-size: 12px; color: #64748b; text-align: center;\">
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
