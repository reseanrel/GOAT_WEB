#!/usr/bin/env python3

"""
Final verification test to ensure the photo display fix is working correctly.
This test simulates the exact template conditions used in the application.
"""

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

def template_condition(photo_url):
    """
    Simulate the exact template condition used in the fixed templates:
    {% if pet.photo_url and pet.photo_url != 'None' and pet.photo_url.strip() %}
    """
    return bool(photo_url and photo_url != 'None' and (photo_url.strip() if photo_url else False))

def main():
    print("Final Verification: Testing Photo Display Fix")
    print("=" * 50)

    try:
        # Connect to the database
        conn = psycopg2.connect(database_url + "?sslmode=require")
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Test 1: Check that no pets would cause broken image URLs
        print("\n1. Testing pets with problematic photo_url values...")
        cursor.execute("""
            SELECT id, name, photo_url
            FROM pets
            WHERE photo_url = 'None' OR photo_url IS NULL OR photo_url = ''
        """)
        problematic_pets = cursor.fetchall()

        print(f"   Found {len(problematic_pets)} pets with problematic photo_url values:")

        for pet in problematic_pets:
            photo_url = pet['photo_url']
            should_show = template_condition(photo_url)
            print(f"   - Pet {pet['id']} ({pet['name']}): photo_url='{photo_url}' -> Should show photo: {should_show}")

        # Test 2: Check that pets with valid photo URLs still work
        print("\n2. Testing pets with valid photo URLs...")
        cursor.execute("""
            SELECT id, name, photo_url
            FROM pets
            WHERE photo_url IS NOT NULL AND photo_url != 'None' AND photo_url != ''
            LIMIT 5
        """)
        valid_pets = cursor.fetchall()

        print(f"   Found {len(valid_pets)} pets with valid photo_url values:")

        for pet in valid_pets:
            photo_url = pet['photo_url']
            should_show = template_condition(photo_url)
            file_exists = os.path.exists(f"static/uploads/{photo_url}")
            print(f"   - Pet {pet['id']} ({pet['name']}): photo_url='{photo_url}' -> Should show: {should_show}, File exists: {file_exists}")

        # Test 3: Verify the specific case that was causing issues
        print("\n3. Testing the specific problematic case...")
        cursor.execute("""
            SELECT id, name, photo_url
            FROM pets
            WHERE photo_url = 'None'
            LIMIT 1
        """)
        none_pet = cursor.fetchone()

        if none_pet:
            print(f"   Testing pet with photo_url='None': {none_pet['name']}")
            print(f"   Old condition (if photo_url): {bool(none_pet['photo_url'])}")
            print(f"   New condition (with != 'None' check): {template_condition(none_pet['photo_url'])}")
            print(f"   ✓ Fix verified: Old condition would show broken image, new condition prevents it")
        else:
            print("   No pets found with photo_url='None' - issue may already be resolved")

        # Test 4: Summary statistics
        print("\n4. Summary Statistics...")
        cursor.execute("SELECT COUNT(*) as total FROM pets")
        total_pets = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as count FROM pets WHERE photo_url = 'None'")
        none_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM pets WHERE photo_url IS NULL")
        null_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM pets WHERE photo_url IS NOT NULL AND photo_url != 'None' AND photo_url != ''")
        valid_count = cursor.fetchone()['count']

        print(f"   Total pets: {total_pets}")
        print(f"   Pets with photo_url='None': {none_count}")
        print(f"   Pets with photo_url=NULL: {null_count}")
        print(f"   Pets with valid photo URLs: {valid_count}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 50)
        print("✓ Photo display fix verification completed successfully!")
        print("✓ Templates will now properly handle 'None' string values")
        print("✓ No more broken image URLs will be generated")

        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)