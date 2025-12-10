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

    print("Checking specific pets that should have photos...")

    # Check pet 819 (Rel) which should have a photo
    cursor.execute("""
        SELECT id, name, photo_url, status, archived
        FROM pets
        WHERE id = 819
    """)
    pet_819 = cursor.fetchone()
    print(f"\nPet 819 (Rel):")
    print(f"  ID: {pet_819['id']}")
    print(f"  Name: {pet_819['name']}")
    print(f"  Photo URL: '{pet_819['photo_url']}'")
    print(f"  Status: {pet_819['status']}")
    print(f"  Archived: {pet_819['archived']}")

    # Check if the file exists
    if pet_819['photo_url']:
        import os
        file_path = f"static/uploads/{pet_819['photo_url']}"
        file_exists = os.path.exists(file_path)
        print(f"  File exists: {file_exists}")
        if file_exists:
            file_size = os.path.getsize(file_path)
            print(f"  File size: {file_size} bytes")

    # Check pet 820 (Diwata) which was recently updated
    cursor.execute("""
        SELECT id, name, photo_url, status, archived
        FROM pets
        WHERE id = 820
    """)
    pet_820 = cursor.fetchone()
    print(f"\nPet 820 (Diwata):")
    print(f"  ID: {pet_820['id']}")
    print(f"  Name: {pet_820['name']}")
    print(f"  Photo URL: '{pet_820['photo_url']}'")
    print(f"  Status: {pet_820['status']}")
    print(f"  Archived: {pet_820['archived']}")

    # Check if the file exists
    if pet_820['photo_url']:
        import os
        file_path = f"static/uploads/{pet_820['photo_url']}"
        file_exists = os.path.exists(file_path)
        print(f"  File exists: {file_exists}")
        if file_exists:
            file_size = os.path.getsize(file_path)
            print(f"  File size: {file_size} bytes")

    # Check all pets for user with ID that owns these pets
    # First find the owner of pet 819
    cursor.execute("""
        SELECT owner_id FROM pets WHERE id = 819
    """)
    owner_id = cursor.fetchone()['owner_id']
    print(f"\nOwner ID: {owner_id}")

    # Check all pets for this owner
    cursor.execute("""
        SELECT id, name, photo_url, status, archived
        FROM pets
        WHERE owner_id = %s AND archived = FALSE AND status = 'approved'
        ORDER BY registered_on DESC
    """, (owner_id,))
    user_pets = cursor.fetchall()

    print(f"\nAll pets for owner {owner_id}:")
    for pet in user_pets:
        print(f"  Pet {pet['id']} ({pet['name']}): photo_url = '{pet['photo_url']}'")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()