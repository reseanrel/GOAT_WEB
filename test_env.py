import os
from dotenv import load_dotenv

load_dotenv()

print("DATABASE_URL:", os.getenv('DATABASE_URL'))
print("GMAIL_USERNAME:", os.getenv('GMAIL_USERNAME'))
print("RESEND_API_KEY:", os.getenv('RESEND_API_KEY'))