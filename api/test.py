from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_test()
    
    def do_POST(self):
        self.handle_test()
    
    def handle_test(self):
        try:
            # Check environment variables
            database_url = os.getenv('DATABASE_URL', 'Not set')
            gmail_user = os.getenv('GMAIL_USER', 'Not set')
            student_code = os.getenv('STUDENT_ACCESS_CODE', 'Not set')
            admin_password = os.getenv('ADMIN_PASSWORD', 'Not set')
            
            # Test database connection
            db_status = "Not connected"
            table_status = {}
            if database_url != 'Not set':
                try:
                    conn = psycopg2.connect(database_url)
                    cursor = conn.cursor()
                    cursor.execute("SELECT version();")
                    db_version = cursor.fetchone()[0]
                    db_status = f"Connected: {db_version}"
                    
                    # Check required tables and their structure
                    required_tables = {
                        'users': ['id', 'name', 'email', 'password', 'created_at'],
                        'quizzes': ['id', 'title', 'description', 'time_limit', 'created_at'],
                        'questions': ['id', 'quiz_id', 'question_text', 'question_type', 'options', 'correct_answer'],
                        'submissions': ['id', 'user_id', 'quiz_id', 'answers', 'score', 'completed_at']
                    }
                    
                    for table, expected_columns in required_tables.items():
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table};")
                            count = cursor.fetchone()[0]
                            
                            # Check columns
                            cursor.execute(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' 
                                ORDER BY ordinal_position;
                            """)
                            actual_columns = [row[0] for row in cursor.fetchall()]
                            
                            missing_cols = set(expected_columns) - set(actual_columns)
                            extra_cols = set(actual_columns) - set(expected_columns)
                            
                            status = f"✅ Exists ({count} rows)"
                            if missing_cols:
                                status += f" | Missing: {list(missing_cols)}"
                            if extra_cols:
                                status += f" | Extra: {list(extra_cols)}"
                                
                            table_status[table] = status
                        except Exception as e:
                            table_status[table] = f"❌ Missing or error: {str(e)}"
                    
                    cursor.close()
                    conn.close()
                except Exception as e:
                    db_status = f"Connection failed: {str(e)}"
            
            response_data = {
                'success': True,
                'message': 'Test endpoint working',
                'environment': {
                    'DATABASE_URL': 'Set' if database_url != 'Not set' else 'Not set',
                    'GMAIL_USER': gmail_user,
                    'STUDENT_ACCESS_CODE': student_code,
                    'ADMIN_PASSWORD': 'Set' if admin_password != 'Not set' else 'Not set'
                },
                'database': {
                    'status': db_status,
                    'tables': table_status
                }
            }
            
            self.send_json_response(response_data)
            
        except Exception as e:
            self.send_json_response({
                'success': False, 
                'message': f'Test failed: {str(e)}'
            })
    
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
