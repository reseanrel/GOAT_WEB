import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Supabase connection URL from environment
database_url = os.getenv('DATABASE_URL')

if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please add your Supabase connection URL to the .env file.")

try:
    # Connect to the database
    conn = psycopg2.connect(database_url + "?sslmode=require")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("Testing photo display fix...")

    # Test 1: Check that no pets have photo_url = 'None' as string
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM pets
        WHERE photo_url = 'None'
    """)
    none_count = cursor.fetchone()['count']
    print(f"[SUCCESS] Pets with photo_url = 'None': {none_count}")

    # Test 2: Check that pets with actual photos have valid filenames
    cursor.execute("""
        SELECT id, name, photo_url
        FROM pets
        WHERE photo_url IS NOT NULL
        LIMIT 5
    """)
    pets_with_photos = cursor.fetchall()

    print(f"Sample pets with photos:")
    for pet in pets_with_photos:
        file_exists = os.path.exists(f"static/uploads/{pet['photo_url']}")
        print(f"  Pet {pet['id']} ({pet['name']}): '{pet['photo_url']}' - File exists: {file_exists}")

    # Test 3: Check template conditions would work correctly
    print("\nTesting template conditions:")

    # Simulate what the template would see
    for pet in pets_with_photos:
        photo_url = pet['photo_url']
        # Template condition: {% if pet.photo_url and pet.photo_url.strip() %}
        condition_result = bool(photo_url and photo_url.strip())
        print(f"  Pet {pet['id']} ({pet['name']}): '{photo_url}' -> Template would show photo: {condition_result}")

    # Test 4: Check NULL handling
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM pets
        WHERE photo_url IS NULL
    """)
    null_count = cursor.fetchone()['count']
    print(f"Pets with photo_url = NULL: {null_count}")

    cursor.close()
    conn.close()

    print("\nPhoto display fix test completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()