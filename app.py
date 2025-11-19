from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



# Database connection
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",       # change if you use another username
    password="mypassword",       # put your MySQL password here
    database="pila_pets_db"
)
cursor = db.cursor(dictionary=True)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'pila-pets-week1-secret-key'

# Email Configuration - Gmail SMTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USERNAME', 'resedelrio9@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD', 'dswqlieetyuezanb')
app.config['COMPANY_NAME'] = 'Pila Pet Registration'

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

        print(f"✅ Verification email sent FROM {app.config['MAIL_USERNAME']} TO {user_email}")
        return True

    except Exception as e:
        print(f"❌ Error sending email to {user_email}: {str(e)}")
        return False

# Authentication Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Fetch user from MySQL
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
            # ✅ Save user info in session
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
        full_name = request.form.get('full_name')
        age = request.form.get('age')
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([full_name, email, password, confirm_password]):
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

        try:
            # ✅ Check for duplicate email in the database
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')

            # Generate verification code
            verification_code = ''.join(random.choices(string.digits, k=6))

            # Store registration data temporarily in session
            session['pending_registration'] = {
                'full_name': full_name,
                'age': age,
                'contact_number': contact_number,
                'address': address,
                'email': email,
                'password': password,
                'verification_code': verification_code
            }

            # Send verification email using Gmail SMTP
            email_sent = send_verification_email(email, verification_code)
            if not email_sent:
                print(f"🔑 FALLBACK: VERIFICATION CODE for {email}: {verification_code}")
                flash('Email service temporarily unavailable. Please check your email later or contact support.', 'warning')
                # Don't return error - allow registration to continue for testing

            flash('Registration form submitted! Please check your email for verification code.', 'success')
            return redirect(url_for('verify_email'))

        except Exception as e:
            print("❌ ERROR:", e)  # 👈 will show actual MySQL or logic error in the terminal
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
                print("❌ ERROR:", e)
                db.rollback()
                flash('An error occurred during account creation. Please try again.', 'error')
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
        print("✅ Email resent successfully via Gmail SMTP")
        return jsonify({'success': True, 'message': 'Verification code resent successfully'})
    else:
        print(f"🔑 FALLBACK: NEW VERIFICATION CODE for {email}: {verification_code}")
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
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
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
    with db.cursor(dictionary=True) as cursor:  
        cursor.execute("SELECT * FROM pets WHERE owner_id = %s", (session['user_id'],))
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
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute("SELECT * FROM pets WHERE owner_id = %s", (session['user_id'],))
    user_pets = cursor.fetchall()
    
    return render_template('user/my_pets.html', 
                         pets=user_pets,
                         user_name=session['user_name'],
                         user_email=session['user_email'],
                         user_contact=session['user_contact'],
                         user_address=session['user_address'])

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
        
        if not name or not category:
            flash('Pet name and category are required', 'error')
            return render_template('user/register_pet.html')

        cursor.execute("""
            INSERT INTO pets (name, category, pet_type, age, color, gender, owner_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, category, pet_type, age, color, gender, session['user_id']))
        db.commit()
        
        flash(f'Pet "{name}" registered successfully!', 'success')
        return redirect(url_for('my_pets'))
    
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
        return redirect(url_for('my_pets'))
    
    # Get owner info from session
    owner_info = {
        'full_name': session['user_name'],
        'email': session['user_email'],
        'contact_number': session['user_contact'],
        'address': session['user_address']
    }
    
    return render_template('user/pet_details.html', pet=pet, owner=owner_info)

@app.route('/user/pet/<int:pet_id>/vaccinations')
@login_required
def vaccination_records(pet_id):
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM pets WHERE id = %s AND owner_id = %s", (pet_id, session['user_id']))
    pet = cursor.fetchone()

    if not pet:
        flash('Access denied', 'error')
        return redirect(url_for('my_pets'))

    # Get vaccinations from database
    cursor.execute("SELECT * FROM vaccinations WHERE pet_id = %s ORDER BY date_administered DESC", (pet_id,))
    pet_vaccinations = cursor.fetchall()

    return render_template('user/vaccination.html', pet=pet, vaccinations=pet_vaccinations)

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

        print(f"✅ Admin notification email sent for lost pet report: {pet_name}")

    except Exception as e:
        print(f"❌ Error sending admin notification email: {str(e)}")

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

        print(f"✅ Admin notification email sent for found pet report: {pet_name}")

    except Exception as e:
        print(f"❌ Error sending admin notification email: {str(e)}")

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
        return redirect(url_for('my_pets'))

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
        WHERE pets.lost = TRUE
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

@app.route('/lost-pet/<int:pet_id>/add-comment', methods=['POST'])
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

        print(f"✅ Admin notification email sent for comment on pet {pet_name}")

    except Exception as e:
        print(f"❌ Error sending admin notification email: {str(e)}")

    return jsonify({'success': True, 'message': 'Comment added successfully'})

@app.route('/user/add-vaccination/<int:pet_id>', methods=['POST'])
@login_required
def add_vaccination(pet_id):
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
    cursor.execute("SELECT COUNT(*) AS total FROM pets")
    total_pets = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE category = 'Dog'")
    dogs = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE category = 'Cat'")
    cats = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM pets WHERE lost = TRUE")
    lost_pets_count = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM comments")
    new_comments_count = cursor.fetchone()['total']

    other_pets = total_pets - dogs - cats

    # Get recent pets with owner information
    cursor.execute("""
    SELECT pets.*, users.full_name AS owner_name
    FROM pets
    JOIN users ON users.id = pets.owner_id
    ORDER BY pets.registered_on DESC
    LIMIT 5
""")
    recent_pets_with_owners = cursor.fetchall()

    return render_template('admin/dashboard.html',
                         total_pets=total_pets,
                         dogs=dogs,
                         cats=cats,
                         lost_pets_count=lost_pets_count,
                         new_comments_count=new_comments_count,
                         other_pets=other_pets,
                         pets=recent_pets_with_owners)

@app.route('/admin/pets')
@login_required
@admin_required
def admin_pets():
    # Get all pets with owner information
    cursor.execute("""
        SELECT pets.*, users.full_name AS owner_name, users.email AS owner_email,
            users.contact_number AS owner_contact, users.address AS owner_address
        FROM pets
        JOIN users ON pets.owner_id = users.id
    """)
    pets_with_owners = cursor.fetchall()
    
    return render_template('admin/pets.html', pets=pets_with_owners)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 5000, debug=True)