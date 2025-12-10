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

    print("Checking for pets with photo_url = 'None'...")

    # First, let's see what unique photo_url values we have
    cursor.execute("""
        SELECT DISTINCT photo_url
        FROM pets
        WHERE photo_url IS NOT NULL
        ORDER BY photo_url
    """)
    distinct_photo_urls = cursor.fetchall()
    print("Distinct photo_url values:")
    for url in distinct_photo_urls:
        print(f"  '{url['photo_url']}'")

    # Find all pets with photo_url = 'None' (case insensitive)
    cursor.execute("""
        SELECT id, name, photo_url
        FROM pets
        WHERE photo_url = 'None' OR photo_url = 'none' OR photo_url = 'NONE'
    """)
    pets_to_fix = cursor.fetchall()

    print(f"Found {len(pets_to_fix)} pets with photo_url = 'None'")

    if pets_to_fix:
        print("Fixing pets:")
        for pet in pets_to_fix:
            print(f"  Pet {pet['id']} ({pet['name']}): {pet['photo_url']} -> NULL")

            # Update the pet to set photo_url to NULL
            cursor.execute("""
                UPDATE pets
                SET photo_url = NULL
                WHERE id = %s
            """, (pet['id'],))

        conn.commit()
        print(f"Fixed {len(pets_to_fix)} pets")

    # Also check for empty strings
    cursor.execute("""
        SELECT id, name, photo_url
        FROM pets
        WHERE photo_url = ''
    """)
    pets_with_empty = cursor.fetchall()

    print(f"Found {len(pets_with_empty)} pets with empty photo_url")

    if pets_with_empty:
        print("Fixing pets with empty photo_url:")
        for pet in pets_with_empty:
            print(f"  Pet {pet['id']} ({pet['name']}): '{pet['photo_url']}' -> NULL")

            # Update the pet to set photo_url to NULL
            cursor.execute("""
                UPDATE pets
                SET photo_url = NULL
                WHERE id = %s
            """, (pet['id'],))

        conn.commit()
        print(f"Fixed {len(pets_with_empty)} pets with empty photo_url")

    # Verify the fix
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM pets
        WHERE photo_url = 'None' OR photo_url = ''
    """)
    remaining_issues = cursor.fetchone()['count']

    print(f"\nVerification: {remaining_issues} pets still have invalid photo_url values")

    if remaining_issues == 0:
        print("✅ All photo_url issues have been fixed!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()