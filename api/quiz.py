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
        query = urlparse(self.path).query
        
        # Handle different quiz endpoints
        # All /api/quiz/* routes come here, check the specific endpoint
        # The path will be like /questions, /list, etc. (without /api/quiz prefix)
        if path.endswith('/questions') or 'quiz_id' in query:
            self.handle_get_questions()
        elif path.endswith('/list'):
            self.handle_get_quizzes()
        else:
            # Default to questions for any other GET request
            self.handle_get_questions()
    
    def do_POST(self):
        # Handle quiz submission - all POST requests go to submit
        self.handle_submit_quiz()
    
    def _connect_db(self):
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception('Database not configured')
        kwargs = {}
        if 'sslmode=' not in database_url.lower():
            kwargs['sslmode'] = 'require'
        return psycopg2.connect(database_url, **kwargs)

    def _column_exists(self, conn, table, column):
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name=%s AND column_name=%s
                )
                """,
                (table, column)
            )
            exists = cur.fetchone()[0]
            cur.close()
            return bool(exists)
        except Exception:
            return False

    def handle_get_questions(self):
        try:
            # Debug logging
            print(f"DEBUG: Path: {self.path}")
            print(f"DEBUG: Headers: {dict(self.headers)}")
            
            query_params = parse_qs(urlparse(self.path).query)
            quiz_id = query_params.get('quiz_id', [None])[0]
            
            print(f"DEBUG: Quiz ID requested: {quiz_id}")
            
            conn = self._connect_db()
            cursor = conn.cursor()
            
            # If no quiz_id provided, get the first available quiz
            if not quiz_id:
                print("DEBUG: No quiz_id provided, getting first quiz")
                cursor.execute("SELECT id FROM quizzes ORDER BY id LIMIT 1")
                result = cursor.fetchone()
                if result:
                    quiz_id = result[0]
                    print(f"DEBUG: Found first quiz with ID: {quiz_id}")
                else:
                    print("DEBUG: No quizzes available in database")
                    self.send_json_response({'success': False, 'message': 'No quizzes available'})
                    return
            
            # Get quiz info
            print(f"DEBUG: Getting quiz info for ID: {quiz_id}")
            cursor.execute("SELECT title, description, time_limit FROM quizzes WHERE id = %s", (quiz_id,))
            quiz_data = cursor.fetchone()
            
            if not quiz_data:
                print(f"DEBUG: Quiz not found for ID: {quiz_id}")
                self.send_json_response({'success': False, 'message': 'Quiz not found'})
                return
            
            print(f"DEBUG: Found quiz: {quiz_data[0]}")
            
            # Get questions with schema detection
            has_qtype = self._column_exists(conn, 'questions', 'question_type')
            has_options = self._column_exists(conn, 'questions', 'options')
            print(f"DEBUG: questions.question_type exists: {has_qtype}")
            print(f"DEBUG: questions.options exists: {has_options}")

            if has_qtype and has_options:
                cursor.execute(
                    """
                    SELECT id, question_text, question_type, options, correct_answer
                    FROM questions WHERE quiz_id = %s ORDER BY id
                    """,
                    (quiz_id,)
                )
                rows = cursor.fetchall()
                questions = []
                for q_id, q_text, q_type, q_options, q_correct in rows:
                    try:
                        opts = json.loads(q_options) if q_options else []
                    except Exception:
                        opts = []
                    # Map essay type to written for frontend compatibility
                    if q_type == 'essay':
                        qtype = 'written'
                    else:
                        qtype = q_type or ('written' if not opts else 'multiple_choice')
                    questions.append({'id': q_id, 'question': q_text, 'type': qtype, 'options': opts, 'correct_answer': q_correct})
            elif has_qtype and not has_options:
                cursor.execute(
                    """
                    SELECT id, question_text, question_type, correct_answer
                    FROM questions WHERE quiz_id = %s ORDER BY id
                    """,
                    (quiz_id,)
                )
                rows = cursor.fetchall()
                questions = []
                for q_id, q_text, q_type, q_correct in rows:
                    # Map essay type to written for frontend compatibility
                    if q_type == 'essay':
                        qtype = 'written'
                    else:
                        qtype = q_type or 'written'
                    questions.append({'id': q_id, 'question': q_text, 'type': qtype, 'options': [], 'correct_answer': q_correct})
            elif not has_qtype and has_options:
                cursor.execute(
                    """
                    SELECT id, question_text, options, correct_answer
                    FROM questions WHERE quiz_id = %s ORDER BY id
                    """,
                    (quiz_id,)
                )
                rows = cursor.fetchall()
                questions = []
                for q_id, q_text, q_options, q_correct in rows:
                    try:
                        opts = json.loads(q_options) if q_options else []
                    except Exception:
                        opts = []
                    qtype = 'written' if not opts else 'multiple_choice'
                    questions.append({'id': q_id, 'question': q_text, 'type': qtype, 'options': opts, 'correct_answer': q_correct})
            else:
                cursor.execute(
                    """
                    SELECT id, question_text, correct_answer
                    FROM questions WHERE quiz_id = %s ORDER BY id
                    """,
                    (quiz_id,)
                )
                rows = cursor.fetchall()
                questions = []
                for q_id, q_text, q_correct in rows:
                    questions.append({'id': q_id, 'question': q_text, 'type': 'written', 'options': [], 'correct_answer': q_correct})

            print(f"DEBUG: Found {len(questions)} questions")
            self.send_json_response({
                'success': True,
                'quiz_id': int(quiz_id),
                'quiz': {'title': quiz_data[0], 'description': quiz_data[1], 'time_limit': quiz_data[2]},
                'questions': questions
            })
            cursor.close(); conn.close()
        except Exception as e:
            print(f"DEBUG: Error in handle_get_questions: {str(e)}"); import traceback; traceback.print_exc()
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_get_quizzes(self):
        try:
            conn = self._connect_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, title, description FROM quizzes ORDER BY id")
            quizzes = []
            
            for row in cursor.fetchall():
                quizzes.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2]
                })
            
            self.send_json_response({
                'success': True,
                'quizzes': quizzes
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def handle_submit_quiz(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            user_id = data.get('user_id')
            quiz_id = data.get('quiz_id')
            answers = data.get('answers', {})
            
            if not all([user_id, quiz_id]):
                self.send_json_response({'success': False, 'message': 'Missing required data'})
                return
            
            conn = self._connect_db()
            cursor = conn.cursor()
            
            # Fetch questions to align indexes and compute details
            cursor.execute("""
                SELECT id, question_text, correct_answer 
                FROM questions 
                WHERE quiz_id = %s
                ORDER BY id
            """, (quiz_id,))
            question_rows = cursor.fetchall()
            
            # Normalize answers: allow list (by index) or dict keyed by question id
            normalized_answers = {}
            if isinstance(answers, list):
                # Map list index -> question id in same order
                for idx, row in enumerate(question_rows):
                    q_id = str(row[0])
                    if idx < len(answers):
                        normalized_answers[q_id] = answers[idx]
            elif isinstance(answers, dict):
                normalized_answers = {str(k): v for k, v in answers.items()}
            else:
                normalized_answers = {}
            
            correct_answers = {str(r[0]): r[2] for r in question_rows}
            question_texts = {str(r[0]): r[1] for r in question_rows}
            
            total_questions = len(question_rows)
            correct_count = 0
            detailed_results = []
            
            for qid in correct_answers.keys():
                user_answer = normalized_answers.get(qid)
                correct_answer = correct_answers[qid]
                is_correct = False
                if user_answer is not None:
                    is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
                if is_correct:
                    correct_count += 1
                detailed_results.append({
                    'question': question_texts[qid],
                    'your_answer': user_answer if user_answer is not None else '',
                    'correct_answer': correct_answer,
                    'is_correct': is_correct
                })
            
            percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
            
            # Save submission
            cursor.execute(
                """
                INSERT INTO submissions (user_id, quiz_id, answers, score, completed_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (user_id, quiz_id, json.dumps(normalized_answers), percentage)
            )
            submission_id = cursor.fetchone()[0]
            conn.commit()
            
            # Optional: send completion email
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                self.send_completion_email(
                    user_data[0],
                    user_data[1],
                    percentage,
                    correct_count,
                    total_questions
                )
            
            # Return a response shape compatible with frontend expectations
            self.send_json_response({
                'success': True,
                'submission_id': submission_id,
                'score': correct_count,               # number of correct answers
                'totalQuestions': total_questions,    # for UI display
                'percentage': round(percentage, 2),
                'correct': correct_count,             # keep legacy keys
                'total': total_questions,             # keep legacy keys
                'feedback': 'Great job!' if percentage >= 60 else 'Keep practicing!',
                'detailed_results': detailed_results
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def send_completion_email(self, name, email, score, correct, total):
        try:
            gmail_user = os.getenv('GMAIL_USER')
            gmail_password = os.getenv('GMAIL_PASSWORD')
            
            if not gmail_user or not gmail_password:
                return
            
            msg = MIMEMultipart()
            msg['From'] = gmail_user
            msg['To'] = email
            msg['Subject'] = "Quiz Completed! 🎯"
            
            # Determine performance level
            if score >= 90:
                performance = "Excellent! 🌟"
                color = "#10b981"
            elif score >= 70:
                performance = "Good job! 👍"
                color = "#3b82f6"
            elif score >= 50:
                performance = "Keep practicing! 📚"
                color = "#f59e0b"
            else:
                performance = "More study needed! 💪"
                color = "#ef4444"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 28px;">Quiz Completed! 🎉</h1>
                </div>
                
                <div style="padding: 30px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                    <h2 style="color: #1e293b;">Hello {name}! 👋</h2>
                    <p style="font-size: 16px; line-height: 1.6;">Congratulations on completing your quiz! Here are your results:</p>
                    
                    <div style="background: white; padding: 25px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="text-align: center;">
                            <div style="font-size: 48px; font-weight: bold; color: {color}; margin-bottom: 10px;">
                                {score:.1f}%
                            </div>
                            <div style="font-size: 18px; color: {color}; font-weight: bold; margin-bottom: 15px;">
                                {performance}
                            </div>
                            <div style="font-size: 16px; color: #64748b;">
                                You answered <strong>{correct} out of {total}</strong> questions correctly
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #e0e7ff; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                        <p style="margin: 0; color: #3730a3;">
                            <strong>💡 Tip:</strong> Keep practicing to improve your knowledge and skills!
                        </p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: none; height: 1px; background: #e2e8f0;">
                    <p style="font-size: 12px; color: #64748b; text-align: center;">
                        This is an automated message from QuizFlow. Thank you for using our platform! 🚀
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
            
        except Exception as e:
            print(f"Email sending failed: {e}")
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
