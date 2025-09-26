from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2
from urllib.parse import parse_qs
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Handle all POST requests to this auth endpoint
        self.handle_login()
    
    def handle_login(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            code = data.get('code', '').strip()
            
            # Validate input
            if not all([name, email, code]):
                self.send_json_response({'success': False, 'message': 'All fields are required'})
                return
            
            # Check if DATABASE_URL is configured
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                self.send_json_response({'success': False, 'message': 'Database not configured'})
                return
            
            # Check access code
            student_code = os.getenv('STUDENT_ACCESS_CODE', '12345')
            if code != student_code:
                self.send_json_response({'success': False, 'message': 'Invalid access code'})
                return
            
            # Connect to database
            try:
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
            except Exception as db_error:
                self.send_json_response({'success': False, 'message': f'Database connection failed: {str(db_error)}'})
                return
            
            # Create user if not exists
            cursor.execute("""
                INSERT INTO users (name, email, password) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (email) DO UPDATE SET 
                    name = EXCLUDED.name,
                    password = EXCLUDED.password
                RETURNING id
            """, (name, email, code))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            # Send welcome email
            self.send_welcome_email(name, email)
            
            self.send_json_response({
                'success': True, 
                'message': 'Login successful',
                'user_id': user_id
            })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': str(e)})
    
    def send_welcome_email(self, name, email):
        try:
            gmail_user = os.getenv('GMAIL_USER')
            gmail_password = os.getenv('GMAIL_PASSWORD')
            
            if not gmail_user or not gmail_password:
                return
            
            msg = MIMEMultipart()
            msg['From'] = gmail_user
            msg['To'] = email
            msg['Subject'] = "Welcome to QuizFlow! 🚀"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #667eea;">Welcome to QuizFlow, {name}! 🎉</h2>
                <p>You have successfully logged into our quiz platform.</p>
                <p>Good luck with your quiz! 🍀</p>
                <hr>
                <p style="font-size: 12px; color: #666;">This is an automated message from QuizFlow.</p>
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
