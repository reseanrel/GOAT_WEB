import psycopg2
from psycopg2.extras import RealDictCursor
import os
import random
import string
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please add your Supabase connection URL to the .env file.")

db = psycopg2.connect(database_url, sslmode='require')
cursor = db.cursor(cursor_factory=RealDictCursor)

def generate_fake_users(num_users=100):
    """Generate fake user data"""
    first_names = [
        'Juan', 'Maria', 'Jose', 'Ana', 'Pedro', 'Rosa', 'Miguel', 'Isabel', 'Antonio', 'Carmen',
        'Francisco', 'Dolores', 'Angel', 'Pilar', 'Manuel', 'Concepcion', 'Rafael', 'Mercedes', 'Fernando', 'Teresa',
        'Carlos', 'Cristina', 'Luis', 'Montserrat', 'Javier', 'Paz', 'Alberto', 'Trinidad', 'Diego', 'Esperanza',
        'Adrian', 'Gloria', 'Sergio', 'Luz', 'Daniel', 'Consuelo', 'Alejandro', 'Asuncion', 'Roberto', 'Celia',
        'Andres', 'Remedios', 'Ramon', 'Milagros', 'Pablo', 'Encarnacion', 'Enrique', 'Chantal', 'Oscar', 'Lourdes'
    ]

    last_names = [
        'Dela Cruz', 'Garcia', 'Rodriguez', 'Gonzalez', 'Fernandez', 'Lopez', 'Martinez', 'Sanchez', 'Perez', 'Martin',
        'Ruiz', 'Hernandez', 'Jimenez', 'Moreno', 'Alvarez', 'Romero', 'Navarro', 'Torres', 'Ramos', 'Gil',
        'Vargas', 'Castillo', 'Guerrero', 'Ortiz', 'Reyes', 'Medina', 'Castro', 'Flores', 'Herrera', 'Gutierrez',
        'Dominguez', 'Santos', 'Aguilar', 'Vega', 'Delgado', 'Pena', 'Leon', 'Mendoza', 'Morales', 'Santiago'
    ]

    addresses = [
        '123 Rizal Street, Pila, Laguna',
        '456 Bonifacio Avenue, Pila, Laguna',
        '789 Mabini Road, Pila, Laguna',
        '321 Luna Street, Pila, Laguna',
        '654 Santos Avenue, Pila, Laguna',
        '987 Reyes Road, Pila, Laguna',
        '147 Cruz Street, Pila, Laguna',
        '258 dela Cruz Avenue, Pila, Laguna',
        '369 Garcia Road, Pila, Laguna',
        '741 Santos Street, Pila, Laguna',
        '852 Rodriguez Avenue, Pila, Laguna',
        '963 Gonzalez Road, Pila, Laguna',
        '159 Fernandez Street, Pila, Laguna',
        '357 Lopez Avenue, Pila, Laguna',
        '468 Martinez Road, Pila, Laguna',
        '579 Sanchez Street, Pila, Laguna',
        '680 Perez Avenue, Pila, Laguna',
        '791 Martin Road, Pila, Laguna',
        '802 Ruiz Street, Pila, Laguna',
        '913 Hernandez Avenue, Pila, Laguna'
    ]

    users = []
    used_emails = set()

    for i in range(num_users):
        # Generate unique email
        email_attempts = 0
        while email_attempts < 10:
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email_base = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
            email = f"{email_base}@gmail.com"

            if email not in used_emails:
                used_emails.add(email)
                break
            email_attempts += 1

        if email_attempts >= 10:
            email = f"user{i+1}@gmail.com"

        # Generate other data
        age = random.randint(18, 70)
        contact_number = f"09{random.randint(100000000, 999999999)}"
        address = random.choice(addresses)
        password = generate_password_hash('password123')  # Default password for testing

        user = {
            'full_name': f"{first_name} {last_name}",
            'age': age,
            'contact_number': contact_number,
            'address': address,
            'email': email,
            'password': password,
            'is_admin': False
        }

        users.append(user)

    return users

def insert_users(users):
    """Insert users into database"""
    try:
        for i, user in enumerate(users, 1):
            cursor.execute("""
                INSERT INTO users (full_name, age, contact_number, address, email, password, is_admin)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user['full_name'],
                user['age'],
                user['contact_number'],
                user['address'],
                user['email'],
                user['password'],
                user['is_admin']
            ))

            if i % 10 == 0:
                print(f"Inserted {i} users...")

        db.commit()
        print(f"Successfully inserted {len(users)} users into the database!")

    except Exception as e:
        print(f"Error inserting users: {e}")
        db.rollback()
        raise

def main():
    print("Generating 100 fake users...")
    users = generate_fake_users(100)

    print("Inserting users into database...")
    insert_users(users)

    print("Done! You can now test the system with 100 users.")
    print("Default login password for all users: password123")

if __name__ == "__main__":
    main()

    # Close database connection
    cursor.close()
    db.close()