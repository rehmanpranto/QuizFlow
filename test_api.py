#!/usr/bin/env python3
"""
Simple test script to verify QuizFlow API endpoints locally.
Run this to test your API functions before deploying to Vercel.
"""

import os
import json
from api.quiz import handler
from api.auth import handler as auth_handler
from api.admin import handler as admin_handler
from unittest.mock import Mock
from io import StringIO
import sys

# Mock environment variables for testing
os.environ['DATABASE_URL'] = 'postgresql://username:password@localhost:5432/quizflow'
os.environ['GMAIL_USER'] = 'test@gmail.com'
os.environ['GMAIL_PASSWORD'] = 'test-password'
os.environ['STUDENT_ACCESS_CODE'] = '12345'
os.environ['ADMIN_PASSWORD'] = 'admin123'

def test_quiz_questions():
    """Test the quiz questions endpoint"""
    print("🧪 Testing Quiz Questions API...")
    
    # Create a mock request
    mock_request = Mock()
    mock_request.path = '/api/quiz/questions?quiz_id=1'
    mock_request.headers = {}
    
    # Capture the response
    response_data = []
    
    def mock_send_response(code):
        response_data.append(f"Status: {code}")
    
    def mock_send_header(name, value):
        response_data.append(f"Header: {name} = {value}")
    
    def mock_end_headers():
        response_data.append("Headers End")
    
    def mock_write(data):
        response_data.append(f"Body: {data.decode()}")
    
    # Mock the handler
    quiz_handler = handler()
    quiz_handler.path = '/questions?quiz_id=1'
    quiz_handler.headers = {}
    quiz_handler.send_response = mock_send_response
    quiz_handler.send_header = mock_send_header
    quiz_handler.end_headers = mock_end_headers
    quiz_handler.wfile = Mock()
    quiz_handler.wfile.write = mock_write
    
    try:
        quiz_handler.do_GET()
        print("✅ Quiz API call completed")
        for item in response_data:
            print(f"   {item}")
    except Exception as e:
        print(f"❌ Quiz API test failed: {e}")
        import traceback
        traceback.print_exc()

def test_database_connection():
    """Test database connection"""
    print("\n🗄️ Testing Database Connection...")
    
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM quizzes")
        quiz_count = cursor.fetchone()[0]
        print(f"✅ Database connected. Found {quiz_count} quizzes")
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        question_count = cursor.fetchone()[0]
        print(f"✅ Found {question_count} questions")
        
        cursor.execute("SELECT id, title FROM quizzes ORDER BY id LIMIT 3")
        quizzes = cursor.fetchall()
        print("📋 Available quizzes:")
        for quiz in quizzes:
            print(f"   ID {quiz[0]}: {quiz[1]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("💡 Make sure to:")
        print("   1. Update DATABASE_URL in this script")
        print("   2. Run database_setup.sql")
        print("   3. Run test_quiz_data.sql")

if __name__ == "__main__":
    print("🚀 QuizFlow API Test Suite")
    print("=" * 40)
    
    # Update this with your actual database URL
    print("⚠️  Update DATABASE_URL in this script before running!")
    print(f"Current DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    print()
    
    test_database_connection()
    test_quiz_questions()
    
    print("\n" + "=" * 40)
    print("🏁 Test completed!")
    print("\n💡 Next steps:")
    print("   1. Update your DATABASE_URL with real credentials")
    print("   2. Make sure your database has the test data")
    print("   3. Deploy to Vercel and test live")
