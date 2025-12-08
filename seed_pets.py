import psycopg2
from psycopg2.extras import RealDictCursor
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please add your Supabase connection URL to the .env file.")

db = psycopg2.connect(database_url, sslmode='require')
cursor = db.cursor(cursor_factory=RealDictCursor)

def get_user_ids():
    """Get all user IDs from database"""
    cursor.execute("SELECT id FROM users WHERE archived = FALSE ORDER BY id")
    users = cursor.fetchall()
    return [user['id'] for user in users]

def get_existing_photos():
    """Get categorized list of existing photo filenames"""
    import os
    uploads_dir = 'static/uploads'
    photos = {
        'dog': [],
        'cat': [],
        'other': []
    }

    if os.path.exists(uploads_dir):
        files = [f for f in os.listdir(uploads_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]

        # Categorize photos based on filename patterns
        for filename in files:
            lower_name = filename.lower()
            if any(keyword in lower_name for keyword in ['dog', 'puppy', 'canine', '1a40e577c1a5af89edfd5c89d0279f11']):
                photos['dog'].append(filename)
            elif any(keyword in lower_name for keyword in ['cat', 'kitten', 'feline', '569846678']):
                photos['cat'].append(filename)
            else:
                photos['other'].append(filename)

        # If no categorized photos, distribute evenly
        if not photos['dog'] and not photos['cat']:
            # Distribute existing photos evenly
            third = len(files) // 3
            photos['dog'] = files[:third]
            photos['cat'] = files[third:2*third]
            photos['other'] = files[2*third:]

    return photos

def generate_fake_pets(num_pets=200):
    """Generate fake pet data"""
    pet_names = [
        'Max', 'Bella', 'Charlie', 'Lucy', 'Buddy', 'Daisy', 'Rocky', 'Molly', 'Jack', 'Sadie',
        'Toby', 'Maggie', 'Bailey', 'Sophie', 'Coco', 'Chloe', 'Bear', 'Lily', 'Duke', 'Zoe',
        'Luna', 'Milo', 'Oliver', 'Nala', 'Leo', 'Simba', 'Tiger', 'Shadow', 'Smokey', 'Ginger',
        'Midnight', 'Princess', 'Oreo', 'Misty', 'Bandit', 'Patches', 'Sasha', 'Lucky', 'Pepper', 'Ruby',
        'Whiskers', 'Muffin', 'Casper', 'Mocha', 'Pumpkin', 'Sunny', 'Cookie', 'Peanut', 'Biscuit', 'Jelly'
    ]

    dog_breeds = [
        'Mixed Breed', 'Labrador Retriever', 'German Shepherd', 'Golden Retriever', 'Bulldog',
        'Poodle', 'Beagle', 'Chihuahua', 'Dachshund', 'Boxer', 'Shih Tzu', 'Pug', 'Great Dane',
        'Siberian Husky', 'Border Collie', 'Cavalier King Charles Spaniel', 'French Bulldog', 'Rottweiler'
    ]

    cat_breeds = [
        'Mixed Breed', 'Persian', 'Maine Coon', 'British Shorthair', 'Ragdoll', 'Siamese',
        'American Shorthair', 'Scottish Fold', 'Sphynx', 'Abyssinian', 'Birman', 'Oriental Shorthair'
    ]

    colors = [
        'Black', 'White', 'Brown', 'Gray', 'Golden', 'Cream', 'Black & White', 'Brown & White',
        'Gray & White', 'Golden & White', 'Black & Brown', 'Tabby', 'Calico', 'Tortoiseshell'
    ]

    pets = []

    for i in range(num_pets):
        # Random pet data
        name = random.choice(pet_names) + str(random.randint(1, 99))
        category = random.choice(['Dog', 'Cat', 'Other'])
        age = random.randint(1, 15)

        if category == 'Dog':
            pet_type = random.choice(dog_breeds)
        elif category == 'Cat':
            pet_type = random.choice(cat_breeds)
        else:
            pet_type = 'Other'

        color = random.choice(colors)
        gender = random.choice(['Male', 'Female'])

        # Random owner
        owner_id = random.choice(user_ids)

        # Random status
        status_roll = random.random()
        if status_roll < 0.7:  # 70% approved
            status = 'approved'
        elif status_roll < 0.8:  # 10% pending
            status = 'pending'
        else:  # 20% rejected
            status = 'rejected'

        # Random lost status (only for approved pets)
        lost = random.random() < 0.15 if status == 'approved' else False  # 15% of approved pets are lost

        # Random adoption availability (only for approved, non-lost pets)
        available_for_adoption = random.random() < 0.25 if (status == 'approved' and not lost) else False

        # Random registration date (last 6 months)
        days_ago = random.randint(0, 180)
        registered_on = datetime.now() - timedelta(days=days_ago)

        # Create pet dict first
        pet = {
            'name': name,
            'category': category,
            'pet_type': pet_type,
            'age': age,
            'color': color,
            'gender': gender,
            'owner_id': owner_id,
            'status': status,
            'lost': lost,
            'available_for_adoption': available_for_adoption,
            'registered_on': registered_on,
            'photo_url': None  # Initialize as None
        }

        # Assign appropriate photo based on pet category (70% chance of having a photo)
        if random.random() < 0.7:
            category_key = pet['category'].lower()
            if category_key in existing_photos and existing_photos[category_key]:
                pet['photo_url'] = random.choice(existing_photos[category_key])
            elif existing_photos['other']:
                # Fallback to other photos if no category-specific photos
                pet['photo_url'] = random.choice(existing_photos['other'])

        pets.append(pet)

    return pets

def insert_pets(pets):
    """Insert pets into database"""
    try:
        for i, pet in enumerate(pets, 1):
            cursor.execute("""
                INSERT INTO pets (name, category, pet_type, age, color, gender, owner_id, status, lost, available_for_adoption, registered_on, photo_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                pet['name'],
                pet['category'],
                pet['pet_type'],
                pet['age'],
                pet['color'],
                pet['gender'],
                pet['owner_id'],
                pet['status'],
                pet['lost'],
                pet['available_for_adoption'],
                pet['registered_on'],
                pet['photo_url']
            ))

            if i % 20 == 0:
                print(f"Inserted {i} pets...")

        db.commit()
        print(f"Successfully inserted {len(pets)} pets into the database!")

    except Exception as e:
        print(f"Error inserting pets: {e}")
        db.rollback()
        raise

def main():
    global user_ids, existing_photos
    print("Getting user IDs from database...")
    user_ids = get_user_ids()

    if len(user_ids) < 10:
        print(f"Warning: Only {len(user_ids)} users found. Consider seeding users first.")
        return

    print("Getting existing photos...")
    existing_photos = get_existing_photos()
    total_photos = sum(len(photos) for photos in existing_photos.values())
    print(f"Found {total_photos} existing photos:")
    print(f"  - Dog photos: {len(existing_photos['dog'])}")
    print(f"  - Cat photos: {len(existing_photos['cat'])}")
    print(f"  - Other photos: {len(existing_photos['other'])}")

    # Clear existing pets and related data to re-seed with photos
    print("Clearing existing pets and related data...")
    cursor.execute("DELETE FROM comments")  # Delete comments first due to foreign key
    cursor.execute("DELETE FROM medical_records")  # Delete medical records
    cursor.execute("DELETE FROM pets")  # Then delete pets
    db.commit()
    print("Cleared existing pets and related data.")

    print(f"Found {len(user_ids)} users. Generating 200 fake pets...")
    pets = generate_fake_pets(200)

    print("Inserting pets into database...")
    insert_pets(pets)

    pets_with_photos = len([p for p in pets if p['photo_url'] is not None])

    print("Done! You can now test the system with pets.")
    print(f"Created approximately:")
    print(f"- {len([p for p in pets if p['status'] == 'approved'])} approved pets")
    print(f"- {len([p for p in pets if p['status'] == 'pending'])} pending pets")
    print(f"- {len([p for p in pets if p['lost']])} lost pets")
    print(f"- {len([p for p in pets if p['available_for_adoption']])} pets available for adoption")
    print(f"- {pets_with_photos} pets with photos ({pets_with_photos/len(pets)*100:.1f}%)")

if __name__ == "__main__":
    main()

    # Close database connection
    cursor.close()
    db.close()