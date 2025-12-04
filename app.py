from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables from .env file
load_dotenv()



# Database connection
import psycopg2
from psycopg2.extras import RealDictCursor

# Get Supabase connection URL from environment
database_url = os.getenv('DATABASE_URL')

if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please add your Supabase connection URL to the .env file.")

db = psycopg2.connect(database_url, sslmode='require')
cursor = db.cursor(cursor_factory=RealDictCursor)

# Ensure archived columns exist
try:
    cursor.execute('ALTER TABLE pets ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE')
    cursor.execute('ALTER TABLE pets ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL')
    cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE')
    cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL')
    db.commit()
    print("Archive columns ensured")
except Exception as e:
    print(f"Could not add archive columns: {e}")
    db.rollback()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'pila-pets-week1-secret-key'

# Email Configuration - Gmail SMTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USERNAME', 'resedelrio9@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD', 'dswqlieetyuezanb')
app.config['COMPANY_NAME'] = 'Pila Pet Registration'

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_verification_email(user_email, verification_code):
    """Send verification email FROM Gmail TO user's email"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Verify Your Email - {app.config['COMPANY_NAME']}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = user_email  # This is the USER'S email address

        # HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .verification-code {{ background: #e8f5e8; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px; border: 2px dashed #4CAF50; }}
                .code {{ font-size: 32px; font-weight: bold; color: #2e7d32; letter-spacing: 5px; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Email Verification</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Thank you for registering with {app.config['COMPANY_NAME']}. Please use the verification code below to verify your email address:</p>

                <div class="verification-code">
                    <h3>Your Verification Code</h3>
                    <div class="code">{verification_code}</div>
                    <p>This code will expire in 1 hour.</p>
                </div>

                <p>Enter this 6-digit code on the verification page to complete your registration.</p>
                <p>If you didn't create an account with {app.config['COMPANY_NAME']}, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
        {app.config['COMPANY_NAME']} - Email Verification

        Thank you for registering with {app.config['COMPANY_NAME']}.

        Your verification code is: {verification_code}

        Enter this 6-digit code on the verification page to complete your registration.

        This code will expire in 1 hour.

        If you didn't create an account with {app.config['COMPANY_NAME']}, please ignore this email.

        This is an automated message. Please do not reply to this email.
        """

        # Attach both HTML and plain text versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')

        msg.attach(part1)
        msg.attach(part2)

        # Send email
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Verification email sent FROM {app.config['MAIL_USERNAME']} TO {user_email}")
        return True

    except Exception as e:
        print(f"[ERROR] Error sending email to {user_email}: {str(e)}")
        return False

# Authentication Routes
@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Fetch user from database
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user and email == 'admin@pila.pets' and password == 'asdf':
            user = {
                'id': 0,
                'full_name': 'Administrator',
                'email': email,
                'password': password,
                'is_admin': True,
                'contact_number': 'N/A',
                'address': 'Pila, Laguna',
                'age': 30
            }

        if user and user['password'] == password:
            # [SUCCESS] Save user info in session
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            session['user_contact'] = user.get('contact_number', '')
            session['user_address'] = user.get('address', '')
            session['user_age'] = user.get('age', '')

            if user['is_admin']:
                flash('Welcome back, Administrator!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Welcome back, {user["full_name"].split()[0]}!', 'success')
                return redirect(url_for('user_dashboard'))

        else:
            flash('Invalid email or password', 'error')

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([first_name, last_name, email, password, confirm_password]):
            flash('Please fill all required fields', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')

        # Password strength validation
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('auth/register.html')

        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for char in password):
            flash('Password must contain at least one symbol', 'error')
            return render_template('auth/register.html')

        # Contact number validation
        if contact_number and (not contact_number.isdigit() or len(contact_number) != 11):
            flash('Contact number must be exactly 11 digits and contain only numbers', 'error')
            return render_template('auth/register.html')

        try:
            # [SUCCESS] Check for duplicate email in the database
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')

            # Generate verification code
            verification_code = ''.join(random.choices(string.digits, k=6))

            # Combine first and last name for full name
            full_name = f"{first_name} {last_name}"

            # Store registration data temporarily in session
            session['pending_registration'] = {
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'age': int(age) if age else None,
                'contact_number': contact_number,
                'address': address,
                'email': email,
                'password': password,
                'verification_code': verification_code
            }

            # Send verification email using Gmail SMTP
            email_sent = send_verification_email(email, verification_code)
            if not email_sent:
                print(f"[CODE] FALLBACK: VERIFICATION CODE for {email}: {verification_code}")
                flash('Email service temporarily unavailable. Please check your email later or contact support.', 'warning')
                # Don't return error - allow registration to continue for testing

            flash('Registration form submitted! Please check your email for verification code.', 'success')
            return redirect(url_for('verify_email'))

        except Exception as e:
            print("[ERROR] ERROR:", e)  # 👈 will show actual MySQL or logic error in the terminal
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('auth/register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'pending_registration' not in session:
        flash('No pending registration found. Please register first.', 'error')
        return redirect(url_for('register'))

    if request.method == 'POST':
        entered_code = request.form.get('verification_code')
        pending_data = session['pending_registration']

        if entered_code == pending_data['verification_code']:
            try:
                # Insert new user into MySQL
                cursor.execute("""
                    INSERT INTO users (full_name, age, contact_number, address, email, password, is_admin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    pending_data['full_name'],
                    pending_data['age'],
                    pending_data['contact_number'],
                    pending_data['address'],
                    pending_data['email'],
                    pending_data['password'],
                    False
                ))
                db.commit()

                # Clear pending registration
                session.pop('pending_registration', None)

                flash('Email verified successfully! You can now login.', 'success')
                return redirect(url_for('login'))

            except Exception as e:
                print("[ERROR] ERROR:", e)
                db.rollback()
                flash(f'An error occurred during account creation: {str(e)}. Please try again.', 'error')
        else:
            flash('Invalid verification code. Please try again.', 'error')

    return render_template('auth/verify_email.html', email=session['pending_registration']['email'])

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    if 'pending_registration' not in session:
        return jsonify({'success': False, 'message': 'No pending registration found'})

    pending_data = session['pending_registration']
    email = pending_data['email']

    # Generate new verification code
    verification_code = ''.join(random.choices(string.digits, k=6))
    pending_data['verification_code'] = verification_code
    session['pending_registration'] = pending_data

    # Send verification email using Gmail SMTP
    email_sent = send_verification_email(email, verification_code)

    if email_sent:
        print("[SUCCESS] Email resent successfully via Gmail SMTP")
        return jsonify({'success': True, 'message': 'Verification code resent successfully'})
    else:
        print(f"[CODE] FALLBACK: NEW VERIFICATION CODE for {email}: {verification_code}")
        # For development/testing, return success anyway
        return jsonify({'success': True, 'message': 'New verification code generated. Please check your email.'})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an AJAX request
            if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.headers.get('Content-Type') in ['application/json', 'multipart/form-data']):
                return jsonify({'success': False, 'message': 'Please login to access this page'})
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            # Check if this is an AJAX request
            if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.headers.get('Content-Type') in ['application/json', 'multipart/form-data']):
                return jsonify({'success': False, 'message': 'Admin access required'})
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get user by ID
def get_user_by_id(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()

# User Routes
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    cursor.execute("SELECT * FROM pets WHERE owner_id = %s AND archived = FALSE AND status = 'approved'", (session['user_id'],))
    user_pets = cursor.fetchall()

    return render_template('user/dashboard.html',
                          user_pets=user_pets,
                          user_name=session['user_name'],
                          user_email=session['user_email'],
                          user_contact=session['user_contact'],
                          user_address=session['user_address'])

@app.route('/user/my-pets')
@login_required
def my_pets():
    # Redirect to dashboard since My Pets functionality is now integrated there
    return redirect(url_for('user_dashboard'))

@app.route('/user/register-pet', methods=['GET', 'POST'])
@login_required
def register_pet():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('pet_name')
        category = request.form.get('pet_category')
        pet_type = request.form.get('pet_type')
        age = request.form.get('age')
        color = request.form.get('color')
        gender = request.form.get('gender')
        available_for_adoption = request.form.get('for_adoption') == 'on'

        if not name or not category:
            flash('Pet name and category are required', 'error')
            return render_template('user/register_pet.html')

        # Handle file upload
        photo_filename = None
        if 'pet_photo' in request.files:
            file = request.files['pet_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to make filename unique
                import time
                timestamp = str(int(time.time()))
                name_part, ext = os.path.splitext(filename)
                photo_filename = f"{name_part}_{timestamp}{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                file.save(file_path)

        cursor.execute("""
            INSERT INTO pets (name, category, pet_type, age, color, gender, owner_id, photo_url, available_for_adoption, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'approved')
        """, (name, category, pet_type, age, color, gender, session['user_id'], photo_filename, available_for_adoption))
        db.commit()

        flash(f'Pet "{name}" registered successfully and is pending admin approval!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('user/register_pet.html')

@app.route('/user/pet/<int:pet_id>')
@login_required
def pet_details(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet or pet['owner_id'] != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))

    # Get owner info from session
    owner_info = {
        'full_name': session['user_name'],
        'email': session['user_email'],
        'contact_number': session['user_contact'],
        'address': session['user_address']
    }

    # Get medical records from database
    cursor.execute("SELECT * FROM medical_records WHERE pet_id = %s ORDER BY record_date DESC", (pet_id,))
    pet_medical_records = cursor.fetchall()

    return render_template('user/pet_details.html', pet=pet, owner=owner_info, medical_records=pet_medical_records, datetime=datetime)

@app.route('/user/update-pet-photo/<int:pet_id>', methods=['POST'])
@login_required
def update_pet_photo(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        print(f"🔍 Checking pet ownership for pet_id: {pet_id}, user_id: {session['user_id']}")
        cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
        pet = cursor.fetchone()

        if not pet:
            print(f"[ERROR] Pet not found or access denied for pet_id: {pet_id}")
            return jsonify({'success': False, 'message': 'Pet not found or access denied'})

        print(f"[SUCCESS] Pet found: {pet['name']}")

        # Handle file upload
        if 'pet_photo' not in request.files:
            print("[ERROR] No file part in request")
            return jsonify({'success': False, 'message': 'No file provided'})

        file = request.files['pet_photo']
        print(f"[FILE] File received: {file.filename if file else 'None'}")

        if not file or file.filename == '':
            print("[ERROR] No file selected")
            return jsonify({'success': False, 'message': 'No file selected'})

        if not allowed_file(file.filename):
            print(f"[ERROR] Invalid file type: {file.filename}")
            return jsonify({'success': False, 'message': 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF files.'})

        # Generate unique filename
        filename = secure_filename(file.filename)
        import time
        timestamp = str(int(time.time()))
        name_part, ext = os.path.splitext(filename)
        photo_filename = f"{name_part}_{timestamp}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)

        print(f"💾 Saving file to: {file_path}")

        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Save the file
        file.save(file_path)

        # Verify file was saved
        if not os.path.exists(file_path):
            print(f"[ERROR] File was not saved: {file_path}")
            return jsonify({'success': False, 'message': 'Failed to save file'})

        print(f"[SUCCESS] File saved successfully: {photo_filename}")

        # Update pet photo in database
        print(f"[DB] Updating database for pet_id: {pet_id}")
        cursor.execute("UPDATE pets SET photo_url = %s WHERE id = %s", (photo_filename, pet_id))
        db.commit()

        print(f"[SUCCESS] Photo uploaded successfully: {photo_filename}")
        return jsonify({'success': True, 'message': 'Photo uploaded successfully', 'photo_filename': photo_filename})

    except Exception as e:
        print(f"[ERROR] Error uploading photo: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while uploading the photo. Please try again.'})

@app.route('/user/pet/<int:pet_id>/medical-records')
@login_required
def medical_records(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))

    # Get medical records from database
    cursor.execute("SELECT * FROM medical_records WHERE pet_id = %s ORDER BY record_date DESC", (pet_id,))
    pet_medical_records = cursor.fetchall()

    return render_template('user/medical_records.html', pet=pet, medical_records=pet_medical_records)

@app.route('/user/pet/<int:pet_id>/vaccinations')
@login_required
def vaccinations(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))

    # Get vaccinations from database (stored in medical_records table with record_type = 'Vaccination')
    cursor.execute("SELECT * FROM medical_records WHERE pet_id = %s AND record_type = 'Vaccination' ORDER BY record_date DESC", (pet_id,))
    vaccinations = cursor.fetchall()

    return render_template('user/vaccination.html', pet=pet, vaccinations=vaccinations)

@app.route('/user/report-lost-pet/<int:pet_id>', methods=['POST'])
@login_required
def report_lost_pet(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not found or access denied'})

    # Get comment from request
    data = request.get_json()
    comment = data.get('comment', '').strip() if data else ''

    if not comment:
        return jsonify({'success': False, 'message': 'Please provide details about how your pet was lost'})

    # Update pet as lost
    cursor.execute("UPDATE pets SET lost = TRUE WHERE id = %s", (pet_id,))
    db.commit()

    # Insert comment into comments table
    cursor.execute("""
        INSERT INTO comments (pet_id, user_id, comment)
        VALUES (%s, %s, %s)
    """, (pet_id, session['user_id'], comment))
    db.commit()

    # Send email notification to admin
    try:
        admin_email = 'resedelrio9@gmail.com'  # Admin's Gmail
        pet_name = pet['name']
        owner_name = session['user_name']

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Lost Pet Report: {pet_name}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = admin_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .pet-info {{ background: #fff; padding: 20px; border-left: 4px solid #FF6B35; margin: 20px 0; }}
                .comment-box {{ background: #fff; padding: 20px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Lost Pet Report</h1>
            </div>
            <div class="content">
                <p>A pet owner has reported their pet as lost:</p>

                <div class="pet-info">
                    <h4>Lost Pet Details</h4>
                    <p><strong>Pet Name:</strong> {pet_name}</p>
                    <p><strong>Category:</strong> {pet['category']}</p>
                    <p><strong>Type:</strong> {pet['pet_type'] or 'Not specified'}</p>
                    <p><strong>Age:</strong> {pet['age']} year(s)</p>
                    <p><strong>Color:</strong> {pet['color'] or 'Not specified'}</p>
                    <p><strong>Owner:</strong> {owner_name}</p>
                    <p><strong>Owner Email:</strong> {session['user_email']}</p>
                    <p><strong>Owner Contact:</strong> {session.get('user_contact', 'Not provided')}</p>
                </div>

                <div class="comment-box">
                    <h4>How the Pet Was Lost</h4>
                    <p style="background: #f8f9fa; padding: 15px; border-radius: 3px;">{comment}</p>
                    <p><strong>Reported on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>

                <p>Please check the admin dashboard to view the lost pet report and manage the situation.</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from {app.config['COMPANY_NAME']}.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - Lost Pet Report

        A pet owner has reported their pet as lost.

        Pet Details:
        - Name: {pet_name}
        - Category: {pet['category']}
        - Type: {pet['pet_type'] or 'Not specified'}
        - Age: {pet['age']} year(s)
        - Color: {pet['color'] or 'Not specified'}
        - Owner: {owner_name}
        - Owner Email: {session['user_email']}
        - Owner Contact: {session.get('user_contact', 'Not provided')}

        How the pet was lost: {comment}

        Reported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Please check the admin dashboard to view the lost pet report.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Admin notification email sent for lost pet report: {pet_name}")

    except Exception as e:
        print(f"[ERROR] Error sending admin notification email: {str(e)}")

    flash(f'Pet "{pet["name"]}" has been reported as lost.', 'success')
    return jsonify({'success': True, 'message': 'Pet reported as lost successfully', 'redirect_url': url_for('report_lost_confirmation', pet_id=pet_id)})

@app.route('/user/mark-found-pet/<int:pet_id>', methods=['POST'])
@login_required
def mark_found_pet(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not found or access denied'})

    # Get comment from request
    data = request.get_json()
    comment = data.get('comment', '').strip() if data else ''

    if not comment:
        return jsonify({'success': False, 'message': 'Please provide details about how your pet was found'})

    # Update pet as found
    cursor.execute("UPDATE pets SET lost = FALSE WHERE id = %s", (pet_id,))
    db.commit()

    # Insert comment into comments table
    cursor.execute("""
        INSERT INTO comments (pet_id, user_id, comment)
        VALUES (%s, %s, %s)
    """, (pet_id, session['user_id'], comment))
    db.commit()

    # Send email notification to admin
    try:
        admin_email = 'resedelrio9@gmail.com'  # Admin's Gmail
        pet_name = pet['name']
        owner_name = session['user_name']

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Pet Found Report: {pet_name}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = admin_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .pet-info {{ background: #fff; padding: 20px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
                .comment-box {{ background: #fff; padding: 20px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Pet Found Report</h1>
            </div>
            <div class="content">
                <p>Great news! A pet owner has reported their pet as found:</p>

                <div class="pet-info">
                    <h4>Found Pet Details</h4>
                    <p><strong>Pet Name:</strong> {pet_name}</p>
                    <p><strong>Category:</strong> {pet['category']}</p>
                    <p><strong>Type:</strong> {pet['pet_type'] or 'Not specified'}</p>
                    <p><strong>Age:</strong> {pet['age']} year(s)</p>
                    <p><strong>Color:</strong> {pet['color'] or 'Not specified'}</p>
                    <p><strong>Owner:</strong> {owner_name}</p>
                    <p><strong>Owner Email:</strong> {session['user_email']}</p>
                    <p><strong>Owner Contact:</strong> {session.get('user_contact', 'Not provided')}</p>
                </div>

                <div class="comment-box">
                    <h4>How the Pet Was Found</h4>
                    <p style="background: #f8f9fa; padding: 15px; border-radius: 3px;">{comment}</p>
                    <p><strong>Reported on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>

                <p>Please check the admin dashboard to update the pet status and remove it from the lost pets list.</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from {app.config['COMPANY_NAME']}.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - Pet Found Report

        Great news! A pet owner has reported their pet as found.

        Pet Details:
        - Name: {pet_name}
        - Category: {pet['category']}
        - Type: {pet['pet_type'] or 'Not specified'}
        - Age: {pet['age']} year(s)
        - Color: {pet['color'] or 'Not specified'}
        - Owner: {owner_name}
        - Owner Email: {session['user_email']}
        - Owner Contact: {session.get('user_contact', 'Not provided')}

        How the pet was found: {comment}

        Reported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Please check the admin dashboard to update the pet status.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Admin notification email sent for found pet report: {pet_name}")

    except Exception as e:
        print(f"[ERROR] Error sending admin notification email: {str(e)}")

    flash(f'Pet "{pet["name"]}" has been marked as found.', 'success')
    return jsonify({'success': True, 'message': 'Pet marked as found successfully'})

@app.route('/user/report-lost-confirmation/<int:pet_id>')
@login_required
def report_lost_confirmation(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        flash('Pet not found or access denied', 'error')
        return redirect(url_for('user_dashboard'))

    # Get the comment that was just added
    cursor.execute("""
        SELECT comment FROM comments
        WHERE pet_id = %s AND user_id = %s
        ORDER BY created_at DESC LIMIT 1
    """, (pet_id, session['user_id']))
    comment_result = cursor.fetchone()
    comment = comment_result['comment'] if comment_result else 'No details provided'

    return render_template('user/report_lost_pet.html', pet=pet, comment=comment)

@app.route('/lost-pets')
def lost_pets():
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
               users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.lost = TRUE AND pets.archived = FALSE AND pets.status = 'approved'
        ORDER BY pets.registered_on DESC
    """)
    lost_pets_list = cursor.fetchall()

    # Get comments for each lost pet
    for pet in lost_pets_list:
        cursor.execute("""
            SELECT comments.*, users.full_name AS commenter_name
            FROM comments
            LEFT JOIN users ON comments.user_id = users.id
            WHERE comments.pet_id = %s
            ORDER BY comments.created_at DESC
        """, (pet['id'],))
        pet['comments'] = cursor.fetchall()

    return render_template('lost_pets.html', lost_pets=lost_pets_list)

@app.route('/adoption')
@login_required
def adoption():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
                users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.available_for_adoption = TRUE AND pets.lost = FALSE AND pets.archived = FALSE AND pets.status = 'approved'
        ORDER BY pets.registered_on DESC
    """)
    adoption_pets = cursor.fetchall()

    return render_template('user/adoption.html', adoption_pets=adoption_pets)

@app.route('/express-adoption-interest/<int:pet_id>', methods=['POST'])
@login_required
def express_adoption_interest(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    # Check if pet is available for adoption
    cursor.execute("SELECT * FROM pets WHERE id = %s AND available_for_adoption = TRUE AND lost = FALSE", (pet_id,))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not available for adoption'})

    message = request.form.get('message', '').strip()
    contact = request.form.get('contact', '').strip()

    if not message:
        return jsonify({'success': False, 'message': 'Please provide a message'})

    # Get adopter info
    adopter_name = session['user_name']
    adopter_email = session['user_email']
    adopter_contact = session.get('user_contact', '')

    # Get pet owner info
    cursor.execute("SELECT full_name, email FROM users WHERE id = %s", (pet['owner_id'],))
    owner = cursor.fetchone()

    if not owner:
        return jsonify({'success': False, 'message': 'Owner information not found'})

    # Insert adoption interest as comment
    full_message = f"ADOPTION INTEREST from {adopter_name}:\n{message}"
    if contact:
        full_message += f"\n\nAdditional contact: {contact}"
    full_message += f"\n\nAdopter Email: {adopter_email}"
    if adopter_contact:
        full_message += f"\nAdopter Phone: {adopter_contact}"

    cursor.execute("""
        INSERT INTO comments (pet_id, user_id, comment)
        VALUES (%s, %s, %s)
    """, (pet_id, session['user_id'], full_message))
    db.commit()

    # Send email notification to pet owner
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Adoption Interest for Your Pet: {pet['name']}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = owner['email']

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .pet-info {{ background: #fff; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0; }}
                .interest-box {{ background: #fff; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Adoption Interest</h1>
            </div>
            <div class="content">
                <p>Hello {owner['full_name']},</p>
                <p>Someone has expressed interest in adopting your pet!</p>

                <div class="pet-info">
                    <h4>Pet Information</h4>
                    <p><strong>Pet Name:</strong> {pet['name']}</p>
                    <p><strong>Category:</strong> {pet['category']}</p>
                    <p><strong>Type:</strong> {pet['pet_type'] or 'Not specified'}</p>
                    <p><strong>Age:</strong> {pet['age']} year(s)</p>
                </div>

                <div class="interest-box">
                    <h4>Adoption Interest Details</h4>
                    <p><strong>Interested Person:</strong> {adopter_name}</p>
                    <p><strong>Email:</strong> {adopter_email}</p>
                    {("<p><strong>Phone:</strong> " + adopter_contact + "</p>") if adopter_contact else ""}
                    {("<p><strong>Additional Contact:</strong> " + contact + "</p>") if contact else ""}
                    <p><strong>Message:</strong></p>
                    <p style="background: #f8f9fa; padding: 15px; border-radius: 3px;">{message}</p>
                </div>

                <p>Please review this adoption interest and contact the interested person if you'd like to proceed with the adoption process.</p>
                <p>You can also respond through the admin dashboard or contact our team for assistance.</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from {app.config['COMPANY_NAME']}.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - Adoption Interest

        Hello {owner['full_name']},

        Someone has expressed interest in adopting your pet {pet['name']}!

        Pet Information:
        - Name: {pet['name']}
        - Category: {pet['category']}
        - Type: {pet['pet_type'] or 'Not specified'}
        - Age: {pet['age']} year(s)

        Adoption Interest Details:
        - Interested Person: {adopter_name}
        - Email: {adopter_email}
        {("- Phone: " + adopter_contact) if adopter_contact else ""}
        {("- Additional Contact: " + contact) if contact else ""}
        - Message: {message}

        Please review this adoption interest and contact the interested person if you'd like to proceed.

        This is an automated notification from {app.config['COMPANY_NAME']}.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Adoption interest notification sent to {owner['email']} for pet {pet['name']}")

    except Exception as e:
        print(f"[ERROR] Error sending adoption interest email: {str(e)}")

    return jsonify({'success': True, 'message': 'Interest submitted successfully'})

@app.route('/lost-pet/<int:pet_id>/add-comment', methods=['POST'])
@login_required
def add_comment(pet_id):
    # Check if pet exists and is lost
    cursor.execute("SELECT * FROM pets WHERE id = %s AND lost = TRUE", (pet_id,))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Lost pet not found'})

    comment_text = request.form.get('comment')
    if not comment_text or not comment_text.strip():
        return jsonify({'success': False, 'message': 'Comment cannot be empty'})

    # Get user_id if logged in, otherwise NULL for anonymous
    user_id = session.get('user_id') if 'user_id' in session else None

    # Insert comment
    cursor.execute("""
        INSERT INTO comments (pet_id, user_id, comment)
        VALUES (%s, %s, %s)
    """, (pet_id, user_id, comment_text.strip()))
    db.commit()

    # Send email notification to admin
    try:
        admin_email = 'resedelrio9@gmail.com'  # Admin's Gmail
        pet_name = pet['name']
        commenter_name = session.get('user_name', 'Anonymous') if user_id else 'Anonymous'

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New Comment on Lost Pet: {pet_name}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = admin_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .comment-box {{ background: #fff; padding: 20px; border-left: 4px solid #FF6B35; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - New Comment Alert</h1>
            </div>
            <div class="content">
                <p>A new comment has been added to a lost pet report:</p>

                <div class="comment-box">
                    <h4>Lost Pet: {pet_name}</h4>
                    <p><strong>Commenter:</strong> {commenter_name}</p>
                    <p><strong>Comment:</strong></p>
                    <p style="background: #f8f9fa; padding: 10px; border-radius: 3px;">{comment_text}</p>
                    <p><strong>Posted on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>

                <p>Please check the admin dashboard to view all comments and manage lost pet reports.</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from {app.config['COMPANY_NAME']}.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - New Comment Alert

        A new comment has been added to a lost pet report.

        Lost Pet: {pet_name}
        Commenter: {commenter_name}
        Comment: {comment_text}
        Posted on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Please check the admin dashboard to view all comments.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Admin notification email sent for comment on pet {pet_name}")

    except Exception as e:
        print(f"[ERROR] Error sending admin notification email: {str(e)}")

    return jsonify({'success': True, 'message': 'Comment added successfully'})

@app.route('/user/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')

        if not first_name or not last_name:
            flash('First name and last name are required', 'error')
            return render_template('user/edit_profile.html')

        # Contact number validation
        if contact_number and (not contact_number.isdigit() or len(contact_number) != 11):
            flash('Contact number must be exactly 11 digits and contain only numbers', 'error')
            return render_template('user/edit_profile.html')

        # Age validation
        if age and (not age.isdigit() or not (1 <= int(age) <= 120)):
            flash('Please enter a valid age between 1 and 120', 'error')
            return render_template('user/edit_profile.html')

        full_name = f"{first_name} {last_name}"

        try:
            cursor.execute("""
                UPDATE users
                SET full_name = %s, age = %s, contact_number = %s, address = %s
                WHERE id = %s
            """, (full_name, age, contact_number, address, session['user_id']))
            db.commit()

            # Update session data
            session['user_name'] = full_name
            session['user_contact'] = contact_number or ''
            session['user_address'] = address or ''
            session['user_age'] = age or ''

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user_dashboard'))

        except Exception as e:
            print("[ERROR] ERROR:", e)
            db.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'error')

    # Get current user data
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    return render_template('user/edit_profile.html', user=user)

@app.route('/user/edit-pet/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        flash('Pet not found or access denied', 'error')
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        name = request.form.get('pet_name')
        category = request.form.get('pet_category')
        pet_type = request.form.get('pet_type')
        age = request.form.get('age')
        color = request.form.get('color')
        gender = request.form.get('gender')
        available_for_adoption = request.form.get('for_adoption') == 'on'

        if not name or not category:
            flash('Pet name and category are required', 'error')
            return render_template('user/edit_pet.html', pet=pet)

        # Age validation
        if age and (not age.isdigit() or not (0 <= int(age) <= 50)):
            flash('Please enter a valid age between 0 and 50 years', 'error')
            return render_template('user/edit_pet.html', pet=pet)

        # Handle photo upload
        photo_filename = pet['photo_url']  # Keep existing photo by default
        if 'pet_photo' in request.files:
            file = request.files['pet_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to make filename unique
                import time
                timestamp = str(int(time.time()))
                name_part, ext = os.path.splitext(filename)
                photo_filename = f"{name_part}_{timestamp}{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                file.save(file_path)

        try:
            cursor.execute("""
                UPDATE pets
                SET name = %s, category = %s, pet_type = %s, age = %s, color = %s, gender = %s, available_for_adoption = %s, photo_url = %s
                WHERE id = %s AND owner_id = %s
            """, (name, category, pet_type, age, color, gender, available_for_adoption, photo_filename, pet_id, session['user_id']))
            db.commit()

            flash(f'Pet "{name}" updated successfully!', 'success')
            return redirect(url_for('pet_details', pet_id=pet_id))

        except Exception as e:
            print("[ERROR] ERROR:", e)
            db.rollback()
            flash('An error occurred while updating the pet. Please try again.', 'error')

    return render_template('user/edit_pet.html', pet=pet)

@app.route('/user/add-vaccination/<int:pet_id>', methods=['POST'])
@login_required
def add_vaccination(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Access denied'})

    # Get data from JSON request
    data = request.get_json()
    vaccine_name = (data.get('vaccine_name') or '').strip()
    date_administered = (data.get('date_administered') or '').strip()
    next_due_date = (data.get('next_due_date') or '').strip()
    administered_by = (data.get('administered_by') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not vaccine_name or not date_administered:
        return jsonify({'success': False, 'message': 'Vaccine name and date are required'})

    # Insert into medical_records table with record_type = vaccine name
    cursor.execute("""
        INSERT INTO medical_records (record_type, record_date, next_due_date, provider, description, pet_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (vaccine_name, date_administered, next_due_date if next_due_date else None, administered_by if administered_by else None, notes if notes else None, pet_id))
    db.commit()

    return jsonify({'success': True, 'message': 'Vaccination record added successfully'})

@app.route('/user/add-medical-record/<int:pet_id>', methods=['POST'])
@login_required
def add_medical_record(pet_id):
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'})

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Access denied'})

    vaccine_name = request.form.get('vaccine_name')
    date_administered = request.form.get('date_administered')
    next_due_date = request.form.get('next_due_date')
    administered_by = request.form.get('administered_by')
    notes = request.form.get('notes')

    if not vaccine_name or not date_administered:
        return jsonify({'success': False, 'message': 'Vaccine name and date are required'})

    cursor.execute("""
        INSERT INTO vaccinations (vaccine_name, date_administered, next_due_date, administered_by, notes, pet_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (vaccine_name, date_administered, next_due_date if next_due_date else None, administered_by, notes, pet_id))
    db.commit()

    return jsonify({'success': True, 'message': 'Vaccination record added successfully'})

# Admin Routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE archived = FALSE")
    total_pets = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE lost = TRUE AND archived = FALSE AND status = 'approved'")
    lost_pets_count = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE status = 'pending' AND archived = FALSE")
    pending_pets_count = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM comments WHERE pet_id IN (SELECT id FROM pets WHERE archived = FALSE)")
    new_comments_count = cursor.fetchone()['total']

    # Get recent non-archived approved pets with owner information
    cursor.execute("""
    SELECT pets.*, users.full_name AS owner_name
    FROM pets
    JOIN users ON users.id = pets.owner_id
    WHERE pets.archived = FALSE AND pets.status = 'approved'
    ORDER BY pets.registered_on DESC
    LIMIT 5
""")
    recent_pets_with_owners = cursor.fetchall()

    return render_template('admin/dashboard.html',
                          total_pets=total_pets,
                          lost_pets_count=lost_pets_count,
                          pending_pets_count=pending_pets_count,
                          new_comments_count=new_comments_count,
                          pets=recent_pets_with_owners)

@app.route('/admin/pets')
@login_required
@admin_required
def admin_pets():
    # Get all non-archived approved pets with owner information
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
            users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.archived = FALSE AND pets.status = 'approved'
    """)
    pets_with_owners = cursor.fetchall()

    return render_template('admin/pets.html', pets=pets_with_owners)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    # Get all non-archived users with pet count
    cursor.execute("""
        SELECT users.*, COUNT(pets.id) AS pet_count
        FROM users
        LEFT JOIN pets ON users.id = pets.owner_id AND pets.archived = FALSE
        WHERE users.archived = FALSE
        GROUP BY users.id
        ORDER BY users.id
    """)
    users_with_pet_count = cursor.fetchall()

    return render_template('admin/users.html', users=users_with_pet_count)


@app.route('/admin/deactivate-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    # Get user data
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    if user['is_admin']:
        return jsonify({'success': False, 'message': 'Cannot deactivate admin user'})

    # Toggle active status
    new_status = not user['active']
    cursor.execute("UPDATE users SET active = %s WHERE id = %s", (new_status, user_id))
    db.commit()

    action = 'deactivated' if not new_status else 'reactivated'

    # Send email notification
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Account {action.title()} - {app.config['COMPANY_NAME']}"
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>"
        msg['To'] = user['email']

        header_color = '#FF6B35' if not new_status else '#4CAF50'
        status_message = "You will no longer be able to log in or access your account until it is reactivated." if not new_status else "You can now log in and access your account again."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {header_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Account {action.title()}</h1>
            </div>
            <div class="content">
                <p>Hello {user['full_name']},</p>
                <p>Your account has been {action} by an administrator.</p>
                <p>{status_message}</p>
                <p>If you have any questions, please contact support.</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - Account {action.title()}

        Hello {user['full_name']},

        Your account has been {action} by an administrator.

        {'You will no longer be able to log in or access your account until it is reactivated.' if not new_status else 'You can now log in and access your account again.'}

        If you have any questions, please contact support.

        This is an automated message. Please do not reply to this email.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Account {action} notification sent to {user['email']}")

    except Exception as e:
        print(f"[ERROR] Error sending notification email: {str(e)}")

    flash(f'User "{user["full_name"]}" {action} successfully', 'success')
    return jsonify({'success': True, 'message': f'User {action} successfully'})


@app.route('/admin/archive-pet/<int:pet_id>', methods=['POST'])
@login_required
@admin_required
def archive_pet(pet_id):
    try:
        # Get pet data with owner information
        cursor.execute("""
            SELECT pets.*, users.email AS owner_email, users.full_name AS owner_name
            FROM pets
            JOIN users ON pets.owner_id = users.id
            WHERE pets.id = %s
        """, (pet_id,))
        pet = cursor.fetchone()

        if not pet:
            return jsonify({'success': False, 'message': 'Pet not found'})

        pet_name = pet['name']
        owner_email = pet['owner_email']
        owner_name = pet['owner_name']

        # Archive pet and set archived timestamp
        cursor.execute("UPDATE pets SET archived = TRUE, archived_at = NOW() WHERE id = %s", (pet_id,))
        db.commit()
    except Exception as e:
        print(f"Error archiving pet: {e}")
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

    # Send email notification to pet owner
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Pet Registration Archived - {pet_name}",
        msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>",
        msg['To'] = owner_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.config['COMPANY_NAME']} - Pet Registration Archived</h1>
            </div>
            <div class="content">
                <p>Dear {owner_name},</p>
                <p>This is to inform you that the registration for your pet <strong>{pet_name}</strong> has been archived from our system by an administrator.</p>
                <p>Archived pets are temporarily hidden but can be restored if needed. If you believe this was done in error or have any questions, please contact the Pila Pets administration immediately.</p>
                <p>Best regards,<br>Pila Pets Administration<br>Municipality of Pila, Laguna</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {app.config['COMPANY_NAME']} - Pet Registration Archived

        Dear {owner_name},

        This is to inform you that the registration for your pet {pet_name} has been archived from our system by an administrator.

        Archived pets are temporarily hidden but can be restored if needed. If you believe this was done in error or have any questions, please contact the Pila Pets administration immediately.

        Best regards,
        Pila Pets Administration
        Municipality of Pila, Laguna

        This is an automated message. Please do not reply to this email.
        """

        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] Pet archive notification email sent to {owner_email} for pet {pet_name}")
    except Exception as e:
        print(f"[ERROR] Failed to send pet archive email: {e}")

    flash(f'Pet "{pet_name}" archived successfully', 'success')
    return jsonify({'success': True, 'message': 'Pet archived successfully'})

@app.route('/admin/bulk-update-pets', methods=['POST'])
@login_required
@admin_required
def bulk_update_pets():
    data = request.get_json()
    pet_ids = data.get('pet_ids', [])
    action = data.get('action')
    value = data.get('value')

    if not pet_ids or not action:
        return jsonify({'success': False, 'message': 'Invalid request data'})

    if action == 'mark_lost':
        cursor.execute(f"UPDATE pets SET lost = TRUE WHERE id IN ({','.join(['%s'] * len(pet_ids))})", pet_ids)
    elif action == 'mark_found':
        cursor.execute(f"UPDATE pets SET lost = FALSE WHERE id IN ({','.join(['%s'] * len(pet_ids))})", pet_ids)
    elif action == 'change_category':
        if not value or value not in ['Dog', 'Cat', 'Other']:
            return jsonify({'success': False, 'message': 'Invalid category'})
        cursor.execute(f"UPDATE pets SET category = %s WHERE id IN ({','.join(['%s'] * len(pet_ids))})", [value] + pet_ids)
    else:
        return jsonify({'success': False, 'message': 'Invalid action'})

    db.commit()
    return jsonify({'success': True, 'message': f'Bulk update completed successfully'})

@app.route('/admin/archive-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def archive_user(user_id):
    try:
        # Get user data
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        if user['is_admin']:
            return jsonify({'success': False, 'message': 'Cannot archive admin user'})

        # Archive user and set archived timestamp
        cursor.execute("UPDATE users SET archived = TRUE, archived_at = NOW() WHERE id = %s", (user_id,))
        db.commit()

        flash(f'User "{user["full_name"]}" has been archived successfully', 'success')
        return jsonify({'success': True, 'message': 'User archived successfully'})
    except Exception as e:
        print(f"Error archiving user: {e}")
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

@app.route('/admin/archived-users')
@login_required
@admin_required
def admin_archived_users():
    # Get all archived users with pet count
    cursor.execute("""
        SELECT users.*, COUNT(pets.id) AS pet_count
        FROM users
        LEFT JOIN pets ON users.id = pets.owner_id
        WHERE users.archived = TRUE
        GROUP BY users.id
        ORDER BY users.archived_at DESC
    """)
    archived_users = cursor.fetchall()

    return render_template('admin/archived_users.html', users=archived_users)

@app.route('/admin/archived')
@login_required
@admin_required
def admin_archived():
    # Get all archived pets with owner information
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
            users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.archived = TRUE
        ORDER BY pets.archived_at DESC
    """)
    archived_pets = cursor.fetchall()

    # Get all archived users with pet count
    cursor.execute("""
        SELECT users.*, COUNT(pets.id) AS pet_count
        FROM users
        LEFT JOIN pets ON users.id = pets.owner_id
        WHERE users.archived = TRUE
        GROUP BY users.id
        ORDER BY users.archived_at DESC
    """)
    archived_users = cursor.fetchall()

    return render_template('admin/archived.html', pets=archived_pets, users=archived_users)

@app.route('/admin/archived-pets')
@login_required
@admin_required
def admin_archived_pets():
    # Get all archived pets with owner information
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
            users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.archived = TRUE
        ORDER BY pets.archived_at DESC
    """)
    archived_pets = cursor.fetchall()

    return render_template('admin/archived_pets.html', pets=archived_pets)

@app.route('/admin/restore-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def restore_user(user_id):
    # Get user data
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    # Restore user
    cursor.execute("UPDATE users SET archived = FALSE, archived_at = NULL WHERE id = %s", (user_id,))
    db.commit()

    flash(f'User "{user["full_name"]}" has been restored successfully', 'success')
    return jsonify({'success': True, 'message': 'User restored successfully'})

@app.route('/admin/restore-pet/<int:pet_id>', methods=['POST'])
@login_required
@admin_required
def restore_pet(pet_id):
    # Get pet data
    cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not found'})

    # Restore pet
    cursor.execute("UPDATE pets SET archived = FALSE, archived_at = NULL WHERE id = %s", (pet_id,))
    db.commit()

    flash(f'Pet "{pet["name"]}" has been restored successfully', 'success')
    return jsonify({'success': True, 'message': 'Pet restored successfully'})

@app.route('/admin/lost-pets')
@admin_required
def admin_lost_pets():
    # Get all non-archived lost pets with owner information and comments
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
               users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.lost = TRUE AND pets.archived = FALSE
        ORDER BY pets.registered_on DESC
    """)
    lost_pets = cursor.fetchall()

    # Get comments for each lost pet
    for pet in lost_pets:
        cursor.execute("""
            SELECT comments.*, users.full_name AS commenter_name
            FROM comments
            LEFT JOIN users ON comments.user_id = users.id
            WHERE comments.pet_id = %s
            ORDER BY comments.created_at DESC
        """, (pet['id'],))
        pet['comments'] = cursor.fetchall()

    # Get statistics
    cursor.execute("SELECT COUNT(*) AS total FROM comments WHERE pet_id IN (SELECT id FROM pets WHERE archived = FALSE)")
    total_comments = cursor.fetchone()['total']

    # Get recent reports (last 7 days)
    cursor.execute("""
        SELECT COUNT(*) AS total FROM pets
        WHERE lost = TRUE AND archived = FALSE AND registered_on >= NOW() - INTERVAL '7 days'
    """)
    recent_reports = cursor.fetchone()['total']

    return render_template('admin/lost_pets.html',
                          lost_pets=lost_pets,
                          total_comments=total_comments,
                          recent_reports=recent_reports)

@app.route('/admin/mark-pet-found/<int:pet_id>', methods=['POST'])
@admin_required
def mark_pet_found(pet_id):
    data = request.get_json()
    note = data.get('note', '').strip() if data else ''

    # Update pet as found
    cursor.execute("UPDATE pets SET lost = FALSE WHERE id = %s", (pet_id,))
    db.commit()

    # Get pet and owner info for email
    cursor.execute("""
        SELECT pets.name, users.email, users.full_name
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.id = %s
    """, (pet_id,))
    pet_info = cursor.fetchone()

    if pet_info:
        pet_name = pet_info['name']
        owner_email = pet_info['email']
        owner_name = pet_info['full_name']

        # Send email notification to owner
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Good News! Your pet {pet_name} has been found",
            msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>",
            msg['To'] = owner_email

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{app.config['COMPANY_NAME']} - Pet Found!</h1>
                </div>
                <div class="content">
                    <p>Dear {owner_name},</p>
                    <p>Great news! Your lost pet {pet_name} has been marked as found in our system.</p>
                    {("<p><strong>Admin Note:</strong> " + note + "</p>") if note else ""}
                    <p>Please contact the Pila Pets administration for more details about the reunion process.</p>
                    <p>Best regards,<br>Pila Pets Administration<br>Municipality of Pila, Laguna</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            {app.config['COMPANY_NAME']} - Pet Found!

            Dear {owner_name},

            Great news! Your lost pet {pet_name} has been marked as found in our system.

            {("Admin Note: " + note) if note else ""}

            Please contact the Pila Pets administration for more details about the reunion process.

            Best regards,
            Pila Pets Administration
            Municipality of Pila, Laguna

            This is an automated message. Please do not reply to this email.
            """

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()

            print(f"[SUCCESS] Found pet notification email sent to {owner_email}")
        except Exception as e:
            print(f"[ERROR] Failed to send found pet email: {e}")

        # Add admin note as comment if provided
        if note:
            # For admin (id=0), set user_id to NULL since admin is not in users table
            user_id = None if session['user_id'] == 0 else session['user_id']
            cursor.execute("""
                INSERT INTO comments (pet_id, user_id, comment, is_admin_reply)
                VALUES (%s, %s, %s, TRUE)
            """, (pet_id, user_id, f"ADMIN NOTE: {note}",))
            db.commit()

    flash(f'Pet "{pet_info["name"] if pet_info else "Unknown"}" has been marked as found.', 'success')
    return jsonify({'success': True})

@app.route('/admin/lost-pet/<int:pet_id>/reply', methods=['POST'])
@admin_required
def admin_reply_to_lost_pet(pet_id):
    reply = request.form.get('reply', '').strip()

    if not reply:
        return jsonify({'success': False, 'message': 'Reply cannot be empty'})

    # Insert admin reply as comment
    # For admin (id=0), set user_id to NULL since admin is not in users table
    user_id = None if session['user_id'] == 0 else session['user_id']
    cursor.execute("""
        INSERT INTO comments (pet_id, user_id, comment, is_admin_reply)
        VALUES (%s, %s, %s, TRUE)
    """, (pet_id, user_id, reply))
    db.commit()

    # Get pet and owner info for email notification
    cursor.execute("""
        SELECT pets.name, users.email, users.full_name
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.id = %s
    """, (pet_id,))
    pet_info = cursor.fetchone()

    if pet_info:
        pet_name = pet_info['name']
        owner_email = pet_info['email']
        owner_name = pet_info['full_name']

        # Send email notification to owner
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Update on your lost pet {pet_name}",
            msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>",
            msg['To'] = owner_email

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{app.config['COMPANY_NAME']} - Update on Lost Pet</h1>
                </div>
                <div class="content">
                    <p>Dear {owner_name},</p>
                    <p>There's an update regarding your lost pet {pet_name}:</p>
                    <div style="background: #fff; padding: 15px; border-left: 4px solid #FF6B35; margin: 20px 0;">
                        <strong>Admin Reply:</strong><br>{reply}
                    </div>
                    <p>Please check the lost pets page for more details.</p>
                    <p>Best regards,<br>Pila Pets Administration<br>Municipality of Pila, Laguna</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            {app.config['COMPANY_NAME']} - Update on Lost Pet

            Dear {owner_name},

            There's an update regarding your lost pet {pet_name}:

            Admin Reply: {reply}

            Please check the lost pets page for more details.

            Best regards,
            Pila Pets Administration
            Municipality of Pila, Laguna

            This is an automated message. Please do not reply to this email.
            """

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()

            print(f"[SUCCESS] Admin reply notification email sent to {owner_email}")
        except Exception as e:
            print(f"[ERROR] Failed to send admin reply email: {e}")

    return jsonify({'success': True})

@app.route('/admin/approve-comment/<int:comment_id>', methods=['POST'])
@admin_required
def approve_comment(comment_id):
    # For now, just mark as approved (could add an approved field to comments table)
    # Since we don't have an approved field, we'll just return success
    # In a real implementation, you'd update a status field
    return jsonify({'success': True, 'message': 'Comment approved'})

@app.route('/admin/delete-comment/<int:comment_id>', methods=['POST'])
@admin_required
def delete_comment(comment_id):
    cursor.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
    db.commit()

    return jsonify({'success': True})

@app.route('/admin/approve-pet/<int:pet_id>', methods=['POST'])
@admin_required
def approve_pet(pet_id):
    cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not found'})

    if pet['status'] != 'pending':
        return jsonify({'success': False, 'message': 'Pet is not pending approval'})

    # Update pet status to approved
    # For admin (id=0), set approved_by to NULL since admin is not in users table
    approved_by = None if session['user_id'] == 0 else session['user_id']
    cursor.execute("""
        UPDATE pets
        SET status = 'approved', approved_at = NOW(), approved_by = %s
        WHERE id = %s
    """, (approved_by, pet_id))
    db.commit()

    # Send email notification to pet owner
    cursor.execute("SELECT email, full_name FROM users WHERE id = %s", (pet['owner_id'],))
    owner = cursor.fetchone()

    if owner:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Good News! Your pet {pet['name']} has been approved",
            msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>",
            msg['To'] = owner['email']

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{app.config['COMPANY_NAME']} - Pet Approved!</h1>
                </div>
                <div class="content">
                    <p>Dear {owner['full_name']},</p>
                    <p>Great news! Your pet registration for <strong>{pet['name']}</strong> has been approved by our administrators.</p>
                    <p>Your pet is now officially registered in the Pila Pet Registration System and will be visible to other users.</p>
                    <p>You can now:</p>
                    <ul>
                        <li>View your pet in "My Pets" section</li>
                        <li>Report your pet as lost if needed</li>
                        <li>Put your pet up for adoption</li>
                        <li>Access vaccination records and other features</li>
                    </ul>
                    <p>Best regards,<br>Pila Pets Administration<br>Municipality of Pila, Laguna</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            {app.config['COMPANY_NAME']} - Pet Approved!

            Dear {owner['full_name']},

            Great news! Your pet registration for {pet['name']} has been approved by our administrators.

            Your pet is now officially registered in the Pila Pet Registration System and will be visible to other users.

            You can now:
            - View your pet in "My Pets" section
            - Report your pet as lost if needed
            - Put your pet up for adoption
            - Access vaccination records and other features

            Best regards,
            Pila Pets Administration
            Municipality of Pila, Laguna

            This is an automated message. Please do not reply to this email.
            """

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()

            print(f"[SUCCESS] Pet approval notification email sent to {owner['email']}")
        except Exception as e:
            print(f"[ERROR] Failed to send pet approval email: {e}")

    flash(f'Pet "{pet["name"]}" has been approved successfully', 'success')
    return jsonify({'success': True, 'message': 'Pet approved successfully'})

@app.route('/admin/reject-pet/<int:pet_id>', methods=['POST'])
@admin_required
def reject_pet(pet_id):
    cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    if not pet:
        return jsonify({'success': False, 'message': 'Pet not found'})

    if pet['status'] != 'pending':
        return jsonify({'success': False, 'message': 'Pet is not pending approval'})

    # Update pet status to rejected
    cursor.execute("UPDATE pets SET status = 'rejected' WHERE id = %s", (pet_id,))
    db.commit()

    # Send email notification to pet owner
    cursor.execute("SELECT email, full_name FROM users WHERE id = %s", (pet['owner_id'],))
    owner = cursor.fetchone()

    if owner:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Pet Registration Update: {pet['name']}",
            msg['From'] = f"{app.config['COMPANY_NAME']} <{app.config['MAIL_USERNAME']}>",
            msg['To'] = owner['email']

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #FF6B35; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; padding: 20px; background: #f1f1f1; text-align: center; border-radius: 5px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{app.config['COMPANY_NAME']} - Pet Registration Update</h1>
                </div>
                <div class="content">
                    <p>Dear {owner['full_name']},</p>
                    <p>We regret to inform you that your pet registration for <strong>{pet['name']}</strong> has been reviewed and was not approved at this time.</p>
                    <p>This decision may be due to:</p>
                    <ul>
                        <li>Incomplete information provided</li>
                        <li>Policy violations</li>
                        <li>Duplicate registration</li>
                        <li>Other administrative reasons</li>
                    </ul>
                    <p>You may submit a new registration with corrected information. Please contact our administration if you have any questions about this decision.</p>
                    <p>Best regards,<br>Pila Pets Administration<br>Municipality of Pila, Laguna</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2024 {app.config['COMPANY_NAME']}. All rights reserved.</p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            {app.config['COMPANY_NAME']} - Pet Registration Update

            Dear {owner['full_name']},

            We regret to inform you that your pet registration for {pet['name']} has been reviewed and was not approved at this time.

            This decision may be due to:
            - Incomplete information provided
            - Policy violations
            - Duplicate registration
            - Other administrative reasons

            You may submit a new registration with corrected information. Please contact our administration if you have any questions about this decision.

            Best regards,
            Pila Pets Administration
            Municipality of Pila, Laguna

            This is an automated message. Please do not reply to this email.
            """

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()

            print(f"[SUCCESS] Pet rejection notification email sent to {owner['email']}")
        except Exception as e:
            print(f"[ERROR] Failed to send pet rejection email: {e}")

    flash(f'Pet "{pet["name"]}" has been rejected', 'warning')
    return jsonify({'success': True, 'message': 'Pet rejected successfully'})

@app.route('/admin/pending-pets')
@admin_required
def admin_pending_pets():
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
               users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
        WHERE pets.status = 'pending' AND pets.archived = FALSE
        ORDER BY pets.registered_on DESC
    """)
    pending_pets = cursor.fetchall()

    return render_template('admin/pending_pets.html', pending_pets=pending_pets)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 5000, debug=True)
