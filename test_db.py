import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Get database URL
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("[ERROR] DATABASE_URL not found in environment variables")
    exit(1)

print("[SUCCESS] DATABASE_URL found")

try:
    # Try to connect
    db = psycopg2.connect(database_url)
    cursor = db.cursor(cursor_factory=RealDictCursor)

    # Test a simple query
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()
    print(f"[SUCCESS] Database connection successful: {result}")

    # Test users table
    cursor.execute("SELECT COUNT(*) as user_count FROM users")
    user_count = cursor.fetchone()
    print(f"[SUCCESS] Users table accessible: {user_count['user_count']} users")

    # Test pets table
    cursor.execute("SELECT COUNT(*) as pet_count FROM pets")
    pet_count = cursor.fetchone()
    print(f"[SUCCESS] Pets table accessible: {pet_count['pet_count']} pets")

    cursor.close()
    db.close()
    print("[SUCCESS] Database test completed successfully")

except Exception as e:
    print(f"[ERROR] Database connection failed: {str(e)}")
    exit(1)
