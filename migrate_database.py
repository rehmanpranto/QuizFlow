#!/usr/bin/env python3
"""
Database migration script to add support for essay questions
Adds missing columns to the questions table
"""

from dotenv import load_dotenv
import psycopg2
import os

# Load environment variables
load_dotenv()

def migrate_database():
    """Add missing columns to support essay questions"""
    try:
        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        print("🔄 Starting database migration...")
        print("Adding support for essay questions to the questions table")
        
        # Check current table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'questions' 
            ORDER BY column_name;
        """)
        
        existing_columns = {row[0] for row in cursor.fetchall()}
        print(f"Current columns: {sorted(existing_columns)}")
        
        migrations_applied = []
        
        # Add question_type column if it doesn't exist
        if 'question_type' not in existing_columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN question_type VARCHAR(50) DEFAULT 'multiple_choice';")
            migrations_applied.append("Added question_type column")
        
        # Add options column if it doesn't exist
        if 'options' not in existing_columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN options JSON;")
            migrations_applied.append("Added options JSON column")
        
        # Modify correct_answer to TEXT to support essay answers
        cursor.execute("ALTER TABLE questions ALTER COLUMN correct_answer TYPE TEXT;")
        migrations_applied.append("Changed correct_answer to TEXT type")
        
        # Make multiple choice option columns nullable for essay questions
        cursor.execute("ALTER TABLE questions ALTER COLUMN option_a DROP NOT NULL;")
        cursor.execute("ALTER TABLE questions ALTER COLUMN option_b DROP NOT NULL;")
        cursor.execute("ALTER TABLE questions ALTER COLUMN option_c DROP NOT NULL;")
        cursor.execute("ALTER TABLE questions ALTER COLUMN option_d DROP NOT NULL;")
        migrations_applied.append("Made option columns nullable")
        
        # Commit all changes
        conn.commit()
        
        print("\n✅ Migration completed successfully!")
        for migration in migrations_applied:
            print(f"  • {migration}")
        
        # Verify the changes
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'questions' 
            ORDER BY column_name;
        """)
        
        print("\n📋 Updated table structure:")
        for row in cursor.fetchall():
            nullable = "NULL" if row[2] == "YES" else "NOT NULL"
            print(f"  • {row[0]}: {row[1]} ({nullable})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Database is now ready for essay questions!")
        print("You can now restart your Flask app and it should work properly.")
    else:
        print("\n💥 Migration failed. Please check the error above.")
