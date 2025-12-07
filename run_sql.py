import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please add your Supabase connection URL to the .env file.")

# Connect to database
conn = psycopg2.connect(database_url)
cursor = conn.cursor()

# Read and execute SQL file
import sys
sql_file = sys.argv[1] if len(sys.argv) > 1 else 'update_vaccinations_to_medical_records.sql'
with open(sql_file, 'r') as file:
    sql_script = file.read()

try:
    cursor.execute(sql_script)
    conn.commit()
    print(f"Successfully executed {sql_file}")
except Exception as e:
    print(f"Error executing {sql_file}: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
