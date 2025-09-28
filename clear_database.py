#!/usr/bin/env python3
"""
Database Cleanup Script for QuizFlow
Clears all quiz data, questions, student submissions, and users while preserving table structure
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_XnpQSx3Jh0bs@ep-gentle-moon-a1u0xdk9-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

def clear_database():
    """Clear all data from the database while preserving table structure"""
    try:
        # Create engine and session
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("🗂️  Connecting to database...")
        
        print("🧹 Clearing database tables...")
        
        # Clear tables in order (respecting foreign key constraints manually)
        tables_to_clear = [
            'submissions',  # Clear submissions first (references users)
            'questions',    # Clear questions next (references quizzes)
            'users',        # Clear users
            'quizzes'       # Clear quizzes last
        ]
        
        for table in tables_to_clear:
            try:
                result = session.execute(text(f"DELETE FROM {table}"))
                row_count = result.rowcount
                print(f"   ✅ Deleted {row_count} records from '{table}' table")
            except Exception as e:
                print(f"   ⚠️  Error clearing '{table}': {e}")
        
        # Try to reset auto-increment sequences (PostgreSQL)
        sequences_to_reset = [
            'users_id_seq',
            'quizzes_id_seq', 
            'questions_id_seq',
            'submissions_id_seq'
        ]
        
        print("🔄 Resetting ID sequences...")
        for seq in sequences_to_reset:
            try:
                session.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                print(f"   ✅ Reset sequence '{seq}'")
            except Exception as e:
                print(f"   ⚠️  Sequence '{seq}' not found or already reset")
        
        # Commit all changes
        session.commit()
        session.close()
        
        print("\n✨ Database cleanup completed successfully!")
        print("📊 Database is now clean with empty tables and reset ID sequences")
        
    except Exception as e:
        print(f"❌ Error during database cleanup: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        sys.exit(1)

def verify_cleanup():
    """Verify that all tables are empty"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("\n🔍 Verifying cleanup...")
        
        tables_to_check = ['users', 'quizzes', 'questions', 'submissions']
        
        for table in tables_to_check:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            status = "✅ Empty" if count == 0 else f"❌ Still has {count} records"
            print(f"   {table}: {status}")
        
        session.close()
        print("✅ Verification complete!")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    print("🧹 QuizFlow Database Cleanup Script")
    print("="*50)
    
    # Confirmation prompt
    response = input("⚠️  This will DELETE ALL quiz data, questions, and student submissions.\nAre you sure you want to continue? (type 'YES' to confirm): ")
    
    if response.strip().upper() == 'YES':
        clear_database()
        verify_cleanup()
        print("\n🎉 Database cleanup completed successfully!")
        print("📝 You can now restart the Flask app to create fresh sample data if needed.")
    else:
        print("❌ Cleanup cancelled.")
        sys.exit(0)
