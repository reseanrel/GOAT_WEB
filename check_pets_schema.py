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

    # Check the schema of the pets table
    print("Checking pets table schema...")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'pets'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()

    print("\nPets table columns:")
    for col in columns:
        print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

    # Check if photo_url column exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'pets' AND column_name = 'photo_url'
        )
    """)
    photo_url_exists = cursor.fetchone()['exists']

    print(f"\nphoto_url column exists in pets table: {photo_url_exists}")

    # Check some sample pet records to see if they have photo_url values
    print("\nSample pet records with photo_url:")
    cursor.execute("""
        SELECT id, name, photo_url
        FROM pets
        WHERE photo_url IS NOT NULL AND photo_url != ''
        LIMIT 5
    """)
    pets_with_photos = cursor.fetchall()

    for pet in pets_with_photos:
        print(f"  Pet {pet['id']} ({pet['name']}): photo_url = '{pet['photo_url']}'")

    # Check if pet_photos table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'pet_photos'
        )
    """)
    pet_photos_table_exists = cursor.fetchone()['exists']

    print(f"\npet_photos table exists: {pet_photos_table_exists}")

    if pet_photos_table_exists:
        print("\nSample pet_photos records:")
        cursor.execute("""
            SELECT * FROM pet_photos LIMIT 5
        """)
        pet_photos = cursor.fetchall()

        for photo in pet_photos:
            print(f"  Photo {photo['id']}: pet_id = {photo['pet_id']}, photo_url = '{photo['photo_url']}'")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()