from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Check environment variables
            env_status = {
                'DATABASE_URL': '✅ Set' if os.getenv('DATABASE_URL') else '❌ Missing',
                'GMAIL_USER': '✅ Set' if os.getenv('GMAIL_USER') else '❌ Missing',
                'GMAIL_PASSWORD': '✅ Set' if os.getenv('GMAIL_PASSWORD') else '❌ Missing',
                'STUDENT_ACCESS_CODE': '✅ Set' if os.getenv('STUDENT_ACCESS_CODE') else '❌ Missing',
                'ADMIN_PASSWORD': '✅ Set' if os.getenv('ADMIN_PASSWORD') else '❌ Missing'
            }
            
            # Check database connection and data
            db_status = {}
            try:
                database_url = os.getenv('DATABASE_URL')
                if not database_url:
                    db_status = {'connection': '❌ No DATABASE_URL'}
                else:
                    kwargs = {}
                    if 'sslmode=' not in database_url.lower():
                        kwargs['sslmode'] = 'require'
                    
                    conn = psycopg2.connect(database_url, **kwargs)
                    cursor = conn.cursor()
                    
                    # Check tables exist
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name IN ('users', 'quizzes', 'questions', 'submissions')
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Count data
                    counts = {}
                    for table in ['users', 'quizzes', 'questions', 'submissions']:
                        if table in tables:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            counts[table] = cursor.fetchone()[0]
                        else:
                            counts[table] = 'Table missing'
                    
                    db_status = {
                        'connection': '✅ Connected',
                        'tables': tables,
                        'data_counts': counts
                    }
                    
                    cursor.close()
                    conn.close()
                    
            except Exception as e:
                db_status = {'connection': f'❌ Error: {str(e)}'}
            
            health_report = {
                'status': 'QuizFlow Health Check',
                'timestamp': '2025-09-26',
                'environment_variables': env_status,
                'database': db_status,
                'recommendations': []
            }
            
            # Add recommendations
            if not os.getenv('DATABASE_URL'):
                health_report['recommendations'].append('Set DATABASE_URL environment variable')
            
            if db_status.get('data_counts', {}).get('quizzes') == 0:
                health_report['recommendations'].append('Run test_quiz_data.sql to add sample quizzes')
            
            if not os.getenv('GMAIL_USER'):
                health_report['recommendations'].append('Set GMAIL_USER and GMAIL_PASSWORD for email notifications')
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(health_report, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
