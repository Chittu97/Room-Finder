from flask import Flask, render_template, request,jsonify, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import decimal
import os
import json
import MySQLdb.cursors
from dotenv import load_dotenv
import random
import smtplib
import re
from datetime import timedelta

app = Flask(__name__, static_folder='static')

# Secret key for session management
app.secret_key = 'abcxyz'

load_dotenv()
sender_email = os.getenv("EMAIL_ADDRESS")
sender_password = os.getenv("EMAIL_PASSWORD")


# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'chittu'
app.config['MYSQL_DB'] = 'room_finder'



UPLOAD_FOLDER = 'static/images/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Initialize MySQL
mysql = MySQL(app)
bcrypt = Bcrypt(app)


# Allowed file extensions for images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_user_status():
    return dict(
        is_logged_in='loggedin' in session and session['loggedin'],
        username=session.get('username'),
        profile_pic=session.get('profile_pic', '/static/images/default-profile.png')
    )

@app.context_processor
def inject_user():
    if 'loggedin' in session:
        # Fetch user from session or database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['id'],))
        user = cursor.fetchone()
        cursor.close()
        if user and not user.get('profile_pic'):
            user['profile_pic'] = 'static/images/uploads/user2.png'  # Default profile picture
        return dict(user=user)
    else:
        return dict(user=None)

# Home/welcome route
@app.route('/')
def welcome():
    return render_template('Welcome-page.html')

@app.route('/roompost')
def roompost():
    return render_template('dashboard.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/ownerpost')
def ownerpost():
    return render_template('roompost_owner.html')

@app.route('/informantpost')
def informantt():
    return render_template('roompost_informant.html')

@app.route('/home')
def home():
    # Ensure the user is logged in
    if 'loggedin' not in session:  # Check if the user is logged in
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    # Fetch user information from session
    user_id = session['id'] if 'id' in session else None
    username = session['username'] if 'username' in session else None

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch data from the `users` table
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        # Default profile image if not set in the `users` table
        if user and not user.get('profile_pic'):
            user['profile_pic'] = 'static/images/uploads/user2.png'

        # Fetch additional profile data from the `profile` table
        cursor.execute("""
            SELECT first_name, last_name, email, role, city, preferred_location, profile_image 
            FROM profile 
            WHERE username = %s
        """, (username,))
        profile_data = cursor.fetchone()  # Fetch profile data from the `profile` table

        # Default values for profile data
        if profile_data:
            profile = {
                'first_name': profile_data['first_name'],
                'last_name': profile_data['last_name'],
                'email': profile_data['email'],
                'role': profile_data['role'],
                'city': profile_data['city'],
                'preferred_location': profile_data['preferred_location'],
                'profile_image': profile_data['profile_image'] if profile_data['profile_image'] else '/static/images/user2.png'
            }
        else:
            profile = {
                'first_name': '',
                'last_name': '',
                'email': '',
                'role': '',
                'city': '',
                'preferred_location': '',
                'profile_image': '/static/images/user2.png'
            }

        cursor.close()

    except Exception as e:
        flash('Error fetching profile data.', 'error')
        print(f"Error: {e}")
        profile = {
            'first_name': '',
            'last_name': '',
            'email': '',
            'role': '',
            'city': '',
            'preferred_location': '',
            'profile_image': '/static/images/user2.png'
        }

    # Pass profile image to the template for navbar display
    return render_template('home-page.html', profile_image = profile.get('profile_image', '/static/images/user2.png'))


    
@app.route('/login', methods=['GET', 'POST'])
def login():
    action = request.args.get("action", "login")  # Default to 'login' section
    msg = ''
    
    if request.method == 'POST':
        if action == 'login':
            user_input = request.form['user_input']
            password = request.form['password']
        
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE username = %s OR phone_number = %s OR email = %s', (user_input, user_input, user_input))
            user = cursor.fetchone()
            cursor.close()
        
            if user and bcrypt.check_password_hash(user['password'], password):
                session['loggedin'] = True
                session['id'] = user['id']
                session['phone_number'] = user['phone_number']
                session['email'] = user['email']
                session['username'] = user['username']
                session['profile_pic'] = user['profile_pic']  # Save profile_pic in session

                # Check if profile exists in the profile table
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('SELECT COUNT(*) FROM profile WHERE id = %s', (user['id'],))
                profile_exists = cursor.fetchone()['COUNT(*)']
                cursor.close()

                if profile_exists == 0:
                    # Insert default profile if it doesn't exist
                    cursor = mysql.connection.cursor()


                    
                    insert_query = """
                        INSERT INTO profile (id, username, first_name, last_name, email,role, city, preferred_location ,created_at , profile_image)
                        VALUES (%s, %s, '', '', %s, '','', '' ,NOW(), '/static/images/default.png')
                    """
                    cursor.execute(insert_query, (user['id'], user['username'],user['email']))
                    mysql.connection.commit()
                    cursor.close()

                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Incorrect username, phone number, email or password!', 'error')

        elif action == 'register':
            username = request.form['username']
            phone_number = request.form['phone_number']
            email = request.form['email']
            password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT id FROM users WHERE username = %s OR phone_number = %s OR email = %s', (username, phone_number, email))
            user = cursor.fetchone()
            
            if user:
                flash('username, Phone number or email already registered!', 'error')
            else:
                default_profile_pic = '/static/images/default-profile.png'
                cursor.execute('INSERT INTO users (username, phone_number, email, password, created_at, profile_pic) VALUES (%s, %s, %s, %s, NOW(), %s)', (username, phone_number, email, password, default_profile_pic))
                mysql.connection.commit()
                flash('Successfully registered! Please log in.', 'success')
                return redirect(url_for('login'))

    return render_template('login-page.html', action=action, msg=msg)

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


#edit profile route
UPLOAD_FOLDER = 'static/images/uploads/profile'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Ensure user is logged in and 'username' exists in session
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))  # Replace 'login' with your login route

    username = session['username']  # Get the username from session
    
    if request.method == 'POST':
        # Handling profile image upload
        if 'profileImage' in request.files:
            profile_image = request.files['profileImage']
            if profile_image and allowed_file(profile_image.filename):
                image_filename = f"{username}_profile_image.{profile_image.filename.rsplit('.', 1)[1].lower()}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                
                try:
                    profile_image.save(image_path)  # Save the image to the folder
                    session['profile_pic'] = f'/static/images/uploads/profile/{image_filename}'  # Store image URL in session
                    flash('Profile image updated successfully!', 'success')
                except Exception as e:
                    flash(f"Error saving the image: {str(e)}", 'error')
                    print(f"Error saving image: {str(e)}")
        
        # Retrieving other form data
        first_name = request.form.get('firstname', '')
        last_name = request.form.get('lastname', '')
        email = request.form.get('email', '')
        role = request.form.get('role', '')
        city = request.form.get('city', '')
        location = request.form.get('location', '')
        
        profile_image_url = session.get('profile_pic', '/static/images/user2.png')  # Default image if not set

        # Update profile in the database
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE profile
            SET first_name = %s, last_name = %s, email = %s, role = %s, city = %s, preferred_location = %s, created_at = NOW(), profile_image = %s 
            WHERE username = %s
        """, (first_name, last_name, email, role, city, location, profile_image_url, username))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile2'))  # Redirect to the same profile page after update
    
    # Render profile page on GET request
    return render_template('profile-page.html', username=username)



# Separate route for uploading profile images
@app.route('/upload-profile-image', methods=['POST'])
def upload_profile_image():
    if 'profileImage' in request.files:
        profile_image = request.files['profileImage']
        if profile_image:
            # Save the image to a specific folder
            image_filename = f"{session['username']}_profile_image.jpg"
            image_path = os.path.join('static/images/uploads/profile', image_filename)
            profile_image.save(image_path)

            # Save the image URL to session
            session['profile_pic'] = f'/static/images/uploads/profile/{image_filename}'

            return jsonify({'success': True, 'image_url': session['profile_pic']})
    
    return jsonify({'success': False, 'message': 'No image uploaded'})





# Multi-Step Form Routes
@app.route('/form1', methods=['GET', 'POST'])
def form1():
    if request.method == 'POST':
        image_names = []

        # Handle file upload
        if 'images' in request.files:  # Correct the file key
            image = request.files['images']
            if image and image.filename != '':
                # Save the file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                image.save(filepath)
                image_names.append(filepath)  # Append file path to image_names list

        # Store form data in session
        session['step1'] = {
            'room_name': request.form.get('room_name', ''),
            'room_type': request.form.get('room_type', ''),
            'gender_preference': request.form.get('gender_preference', ''),
            'furnished_status': request.form.get('furnished_status', ''),
            'occupancy_limit': request.form.get('occupancy_limit', ''),
            'attached_facilities': request.form.getlist('attached_facilities'),
            'roompost_date': request.form.get('roompost_date', ''),
            'room_images': image_names,  # Saved image paths
        }

        # Debugging: Print session data in terminal
        print("Session data:", session['step1'])

        # Redirect to the next form
        return redirect(url_for('form2'))
    
    # Render form1 template with pre-filled data if available
    return render_template('owner-form/form1.html', data=session.get('step1', {}))


@app.route('/form2', methods=['GET', 'POST'])
def form2():
    if request.method == 'POST':
        # Store form data in session
        session['step2'] = {
            'city': request.form['city'],
            'pin_code': request.form['pin_code'],
            'locality': request.form['locality'],
            'landmark': request.form['landmark'],
            'address': request.form['address'],
            'nearby_facilities': request.form.getlist('nearby_facilities')  # Handles multiple checkbox values
        }

        return redirect(url_for('form3'))  # Correct: Redirect to form3

    return render_template('owner-form/form2.html', data=session.get('step2', {}))  # Pre-filled

@app.route('/form3', methods=['GET', 'POST'])
def form3():
    if request.method == 'POST':
        # Store form data in session
        session['step3'] = {
            'monthly_rent': request.form['monthly_rent'],
            'utilities_included': request.form.getlist('utilities_included'),  # Handles multiple checkbox values
            'advanced_payment': request.form['advanced_payment']
        }

        return redirect(url_for('form4'))  # Correct: Redirect to form4

    return render_template('owner-form/form3.html', data=session.get('step3', {}))  # Pre-filled

@app.route('/form4', methods=['GET', 'POST'])
def form4():
    if request.method == 'POST':
        # Store form data in session
        session['step4'] = {
            'furnishing': request.form['furnishing'],  # Single selection dropdown
            'bed': request.form['bed'],  # Single selection dropdown
            'bathroom': request.form['bathroom'],  # Single selection dropdown
            'kitchen': request.form['kitchen'],  # Single selection dropdown
            'ac': request.form['ac'],  # Single selection dropdown
            'parking': request.form['parking'],  # Single selection dropdown
            'common_facilities': request.form.getlist('common-facilities')  # Handles multiple checkbox values
        }
        return redirect(url_for('form5'))  # Correct: Redirect to form5

    return render_template('owner-form/form4.html', data=session.get('step4', {}))  # Pre-filled

@app.route('/form5', methods=['GET', 'POST'])
def form5():
    if request.method == 'POST':
        # Store form data in session
        session['step5'] = {
            'full_name': request.form['full_name'],  # Single input field
            'phone': request.form['phone'],  # Single input field
            'alternate_phone': request.form.get('alternate_phone', ''),  # Optional input field
            'email': request.form['email'],  # Single input field
            'communication': request.form.getlist('communication'),  # Multiple checkbox values
            'visit_address': request.form.get('visit_address', '')  # Optional textarea
        } 
        return redirect(url_for('form6'))  # Correct: Redirect to form6

    return render_template('owner-form/form5.html', data=session.get('step5', {}))  # Pre-filled

@app.route('/form6', methods=['GET', 'POST'])
def form6():
    if request.method == 'POST':
        # Store form data in session
        session['step6'] = {
            'additional_amenities': request.form.getlist('additional_amenities'),  # List of selected checkboxes
            'tenant_type': request.form['tenant_type'],  # Single select field
            'other_comments': request.form.get('other_comments', '')  # 
        } 
        return redirect(url_for('confirmation'))  # Correct: Redirect to confirmation

    return render_template('owner-form/form6.html', data=session.get('step6', {}))  # Pre-filled

@app.route('/confirmation', methods=['GET'])
def confirmation():
    # Combine all session data
    data = {
        **session.get('step1', {}),
        **session.get('step2', {}),
        **session.get('step3', {}),
        **session.get('step4', {}),
        **session.get('step5', {}),
        **session.get('step6', {})
    }
    return render_template('confirmation/confirm1.html', data=data)


@app.route('/submit_form', methods=['GET', 'POST'])
def submit_form():
    if request.method == 'POST':
        # Step 1: Collect data from the session for all steps
        room_data = {**session.get('step1', {}), **session.get('step2', {}), 
                     **session.get('step3', {}), **session.get('step4', {}), 
                     **session.get('step5', {}), **session.get('step6', {})}
        print("Room Data:", room_data)



        # Fetch necessary fields for duplication check
        room_name = room_data.get('room_name', 'Not Provided')
        gender_preference = room_data.get('gender_preference', 'Not Provided')
        address = room_data.get('address', 'Not Provided')
        city = room_data.get('city', 'Not Provided')
        phone = room_data.get('phone', 'Not Provided')

        # Check if room already exists in the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''SELECT * FROM rooms 
                          WHERE room_name = %s AND gender_preference = %s AND address = %s AND city = %s AND phone_number = %s''',
                       (room_name, gender_preference,  address, city, phone))
        existing_room = cursor.fetchone()

        if existing_room:
            # Alert message if duplicate data exists
            flash(f"A room with the name '{room_name}' at address '{address}'  in '{city}' already exists. Please post a different room.", 'warning')
            
            # Redirect to confirmation page without clearing session
            return redirect(url_for('confirmation'))

        # If no duplicate is found, insert data into the database
        # Prepare data for insertion (example logic shown here, complete as per your original code)

        # Prepare data for insertion into the database
        room_name = room_data.get('room_name', 'Not Provided')
        room_type = room_data.get('room_type', 'Not Provided')
        gender_preference = room_data.get('gender_preference', 'Not Provided')
        furnished_status = room_data.get('furnished_status', 'Not Provided')
        occupancy_limit = room_data.get('occupancy_limit', 'Not Provided')

        # Handling multiple checkboxes (attached facilities)
        attached_facilities = room_data.get('attached_facilities', [])

        # Room Images
        room_images = room_data.get('room_images', [])

        # Posting Date
        roompost_date = room_data.get('roompost_date', 'Not Provided')

        # Location Details
        city = room_data.get('city', 'Not Provided')
        zip_code = room_data.get('pin_code', 'Not Provided')
        locality = room_data.get('locality', 'Not Provided')
        landmark = room_data.get('landmark', 'Not Provided')
        address = room_data.get('address', 'Not Provided')

        # Handling multiple checkboxes (nearby facilities)
        nearby_facilities = room_data.get('nearby_facilities', [])

        # Pricing Information
        monthly_rent = room_data.get('monthly_rent', 'Not Provided')
        utilities_included = room_data.get('utilities_included', [])
        advanced_payment = room_data.get('advanced_payment', 'Not Provided')

        # Room Features and Amenities
        furnishing = room_data.get('furnishing', 'Not Provided')
        bed = room_data.get('bed', 'Not Provided')
        bathroom = room_data.get('bathroom', 'Not Provided')
        kitchen = room_data.get('kitchen', 'Not Provided')
        ac = room_data.get('ac', 'Not Provided')
        parking = room_data.get('parking', 'Not Provided')

        # Handling multiple checkboxes (common facilities)
        common_facilities = room_data.get('common_facilities', [])

        # Contact Information
        full_name = room_data.get('full_name', 'Not Provided')
        phone= room_data.get('phone', 'Not Provided')
        alternate_phone = room_data.get('alternate_phone', '') or 'NULL'
        email = room_data.get('email', 'Not Provided')

        # Handling multiple checkboxes (communication preferences)
        communication_preference = room_data.get('communication', [])
        visit_address = room_data.get('visit_address', 'Not Provided')

        # Additional Information
        additional_amenities = room_data.get('additional_amenities', [])
        tenant_type = room_data.get('tenant_type', 'Not Provided')
        other_comments = room_data.get('other_comments', 'Not Provided')

        # Convert list to JSON string if there are any values, otherwise set to NULL
        if attached_facilities:
             attached_facilities_json = json.dumps(attached_facilities)  # Converts list to JSON string
        else:
            attached_facilities_json = None  # Use None for NULL in MySQL

            # Convert list to JSON string if there are any values, otherwise set to NULL
        if room_images:
            room_images_json = json.dumps(room_images)  # Converts list to JSON string
        else:
            room_images_json = None  # Use None for NULL in MySQL

        if nearby_facilities:
            nearby_facilities_json = json.dumps(nearby_facilities)  # Converts list to JSON string
        else:
            nearby_facilities_json = None  # Use None for NULL in MySQL (or use json.dumps([]) for an empty array)

        if utilities_included:
            utilities_included_json = json.dumps(utilities_included)  # Converts list to JSON string
        else:
            utilities_included_json = None  # Use None for NULL in MySQL (or use json.dumps([]) for an empty array)


        # Ensure it is properly formatted as a JSON string
        if common_facilities:
            common_facilities_json = json.dumps(common_facilities)  # Converts list to JSON string
        else:
            common_facilities_json = None  # Use None for NULL in MySQL (or json.dumps([]) for an empty array)


        if communication_preference:
            communication_preference_json = json.dumps(communication_preference)  # Converts list to JSON string
        else:
            communication_preference_json = None  # Use None for NULL in MySQL (or json.dumps([]) for an empty array)
  
        if additional_amenities:
            additional_amenities_json = json.dumps(additional_amenities)  # Convert to JSON string  
        else:
             additional_amenities_json = None  # Use None for NULL in MySQL (or json.dumps([])

        # Step 2: Insert data into the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''INSERT INTO rooms 
                        (room_name, room_type, gender_preference, furnished_status, occupancy_limit, 
                        attached_facilities, room_images, room_posting_date, city, zip_code, locality, 
                        landmark, address, nearby_facilities, monthly_rent, utility_included, 
                        advanced_payment, room_furnishing, bed_availability, bathroom_type, kitchen_facility, air_conditioning, parking_facility, 
                        common_facilities, contact_name, phone_number, alt_phone_number, email_address, communication_preference, 
                        visit_address, additional_amenities, preferred_tenant_type, other_comments) 
                        VALUES (%s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
''', 
                       (room_name, room_type, gender_preference, furnished_status, occupancy_limit,
                        attached_facilities_json, room_images_json, roompost_date, city, zip_code, locality,
                        landmark, address, nearby_facilities_json, monthly_rent, utilities_included_json,
                        advanced_payment, furnishing, bed, bathroom, kitchen, ac, parking,
                        common_facilities_json, full_name, phone, alternate_phone, email, communication_preference_json,
                        visit_address, additional_amenities_json, tenant_type, other_comments))

        # Commit the transaction
        mysql.connection.commit()

        # Clear the session after successful submission
        session.clear()


        # Flash a success message
        flash("Room details submitted successfully!",'success')

        # Redirect to the home page
        return redirect(url_for('rooms'))

    # Handle GET request (optional)
    return redirect(url_for('rooms'))

@app.route('/in_form1', methods=['GET', 'POST'])
def in_form1():
    if request.method == 'POST':
        image_names = []

        # Handle file upload
        if 'images' in request.files:  # Correct the file key
            image = request.files['images']
            if image and image.filename != '':
                # Save the file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                image.save(filepath)
                image_names.append(filepath)  # Append file path to image_names list

         

        # Store form data in session
        session['step1'] = {
            'room_name': request.form['room_name'],
            'room_type': request.form['room_type'],
            'gender_preference': request.form['gender_preference'],
            'roompost_date': request.form['roompost_date'],
            'room_images': image_names,  # Store filenames, not raw file objects
        }
        print(session['step1'])

        return redirect(url_for('in_form2'))  # Redirect to the next form

    return render_template('informant-form/in_form1.html', data=session.get('step1', {}))  # Pre-filled form data if available

@app.route('/in_form2', methods=['GET', 'POST'])
def in_form2():
    if request.method == 'POST':
        # Store form data in session
        session['step2'] = {
            'city': request.form['city'],
            'pin_code': request.form['pin_code'],
            'locality': request.form['locality'],
            'landmark': request.form['landmark'],
            'address': request.form['address'],
        }

        return redirect(url_for('in_form3'))  # Correct: Redirect to form3

    return render_template('informant-form/in_form2.html', data=session.get('step2', {}))  # Pre-filled

@app.route('/in_form3', methods=['GET', 'POST'])
def in_form3():
    if request.method == 'POST':
        # Store form data in session
        session['step3'] = {
            'full_name': request.form['full_name'],  # Single input field
            'owners_name': request.form['owners_name'] ,
            'owners_phone': request.form.get('owners_phone',''),  # Single input field
            'alternate_phone': request.form.get('alternate_phone', ''),  # Optional input field
          
        } 
        return redirect(url_for('confirmation2'))  # Correct: Redirect to form6

    return render_template('informant-form/in_form3.html', data=session.get('step3', {}))  # Pre-filled


@app.route('/confirmation2', methods=['GET'])
def confirmation2():
    # Combine all session data
    data = {
        **session.get('step1', {}),
        **session.get('step2', {}),
        **session.get('step3', {}),
       
    }
    return render_template('confirmation/confirm2.html', data=data)


@app.route('/submit_form2', methods=['GET', 'POST'])
def submit_form2():
    if request.method == 'POST':
        # Step 1: Collect data from the session for all steps
        room_data = {**session.get('step1', {}), **session.get('step2', {}), 
                     **session.get('step3', {})}
        print("Room Data:", room_data)

        # Fetch necessary fields for duplication check
        room_name = room_data.get('room_name', 'Not Provided')
        gender_preference = room_data.get('gender_preference', 'Not Provided')
        address = room_data.get('address', 'Not Provided')
        city = room_data.get('city', 'Not Provided')
        phone = room_data.get('owners_phone', 'Not Provided')

        # Check if room already exists in the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        print(f"Query: SELECT * FROM rooms2 WHERE room_name = {room_name}, gender_preference = {gender_preference}, address = {address}, city = {city}, owners_phone = {phone}", flush=True)

        cursor.execute('''SELECT * FROM rooms2 
                          WHERE room_name = %s AND gender_preference = %s AND address = %s AND city = %s AND owners_phone = %s''',
                       (room_name, gender_preference,  address, city, phone))
        existing_room = cursor.fetchone()
        print(f"Existing Room: {existing_room}",flush=True)


        if existing_room:
            # Alert message if duplicate data exists
            flash(f"A room with the name '{room_name}' at address '{address}' in '{city}' already exists. Please post a different room.", 'warning')
            
            # Redirect to confirmation page without clearing session
            return redirect(url_for('confirmation2'))

        # If no duplicate is found, insert data into the database
        # Prepare data for insertion (example logic shown here, complete as per your original code)

# basic rooom information
        room_name = room_data.get('room_name', 'Not Provided')
        room_type = room_data.get('room_type', 'Not Provided')
        gender_preference = room_data.get('gender_preference', 'Not Provided')
        room_images = room_data.get('room_images', [])

        # Posting Date
        roompost_date = room_data.get('roompost_date', 'Not Provided')


#location details

        city = room_data.get('city', 'Not Provided')
        zip_code = room_data.get('pin_code', 'Not Provided')
        locality = room_data.get('locality', 'Not Provided')
        landmark = room_data.get('landmark', 'Not Provided')
        address = room_data.get('address', 'Not Provided')

        # contact infomation

        full_name = room_data.get('full_name', 'Not Provided')
        owners_name = room_data.get('owners_name', 'Not Provided')
        owners_phone= room_data.get('owners_phone', 'Not Provided')
        alternate_phone = room_data.get('alternate_phone', '') or 'NULL'

        if room_images:
            room_images_json = json.dumps(room_images)  # Converts list to JSON string
        else:
            room_images_json = None  # Use None for NULL in 
            
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''INSERT INTO rooms2
                    (room_name, room_type, gender_preference, room_images, room_posting_date, city, pin_code, locality, 
                    landmark, address, full_name, owners_name, owners_phone, alternate_phone) 
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                   (room_name, room_type, gender_preference, room_images_json, roompost_date, city, zip_code, locality,
                    landmark, address, full_name, owners_name, owners_phone, alternate_phone))


        # Commit the transaction
        mysql.connection.commit()

        # Clear the session after successful submission
        session.clear()


        # Flash a success message
        flash("Room details submitted successfully!",'success')

        # Redirect to the home page
        return redirect(url_for('rooms'))

    # Handle GET request (optional)
    return redirect(url_for('rooms'))
    
# Route to fetch and display paginated data

@app.route('/rooms')
def rooms():
    cursor = None
    try:
        # Create a cursor object using MySQL connection
        cursor = mysql.connection.cursor()

        # Get sort order from the request (default is 'latest')
        sort_order = request.args.get('sort', 'latest')  # default to 'latest'

        # Create the base query for fetching room details from both tables
        query_combined = """
        SELECT room_name, room_images, gender_preference, city, address, 'owner' AS table_name, id
        FROM rooms
        UNION ALL
        SELECT room_name, room_images, gender_preference, city, address, 'informant' AS table_name, id
        FROM rooms2
        """

        # Apply sorting based on the selected sort order
        if sort_order == 'latest':
            query_combined += " ORDER BY id DESC"  # Latest first
        elif sort_order == 'oldest':
            query_combined += " ORDER BY id ASC"   # Oldest first

        cursor.execute(query_combined)
        combined_rooms = cursor.fetchall()

        # Pass the data and the sort order to the template
        return render_template('rooms.html', combined_rooms=combined_rooms, sort_order=sort_order)

    except Exception as e:
        # Handle exception and pass the error message to the template
        error_message = f"An error occurred: {e}"
        return render_template('rooms.html', error_message=error_message)

    finally:
        # Ensure cursor is closed after operation
        if cursor:
            cursor.close()


@app.before_request
def clear_session_on_refresh():
    # Check if the request is a refresh (i.e., GET request) and clear session
    if request.method == 'GET':
        session.pop('city_query', None)  # Clear the session key for city_query


@app.route('/search', methods=['GET'])
def search_rooms():
    cursor = None
    try:
        # Get the search query from request arguments
        city_query = request.args.get('city', '').strip()

        if city_query:
            session['city_query'] = city_query  # Store city query in session
        else:
            session.clear()  # Clear session if search query is empty
        city_query = session.get('city_query', '')  # Get city from session if exists

        if not city_query:
            # If no city provided, show an error or empty search results
            return render_template('search_results.html', combined_rooms=[], error_message="Please provide a city to search.")

        # Create a cursor object using MySQL connection
        cursor = mysql.connection.cursor()

        # Fetch data from both tables with a city filter
        search_query = f"""
        SELECT room_name, room_images, gender_preference, city, address, 'owner' AS table_name, id
        FROM rooms
        WHERE city LIKE %s
        UNION ALL
        SELECT room_name, room_images, gender_preference, city, address, 'informant' AS table_name, id
        FROM rooms2
        WHERE city LIKE %s;
        """
        # Execute query with the user-provided city
        like_query = f"%{city_query}%"  # Allow partial matches
        cursor.execute(search_query, (like_query, like_query))

        # Fetch the filtered results
        combined_rooms = cursor.fetchall()

        # Render the search results page with filtered data
        return render_template('search_results.html', combined_rooms=combined_rooms, city_query=city_query)

    except Exception as e:
        # Handle exception and pass the error message to the template
        error_message = f"An error occurred: {e}"
        return render_template('search_results.html', combined_rooms=[], error_message=error_message)

    finally:
        # Ensure cursor is closed after operation
        if cursor:
            cursor.close()


@app.route('/filtered_rooms', methods=['GET'])
def filtered_rooms():
    cursor = None
    try:
        # Retrieve filter values from query parameters
        city = request.args.get('city')
        room_type = request.args.get('room_type')
        gender_preference = request.args.get('gender_preference')
        print("Filters Received:", city, room_type, gender_preference)

        # Base query for rooms and rooms2
        query_rooms = """
        SELECT room_name, room_type, gender_preference, city, address, 'owner' AS table_name, id
        FROM rooms
        WHERE 1=1
        """
        query_rooms2 = """
        SELECT room_name, room_images, gender_preference, city, address, 'informant' AS table_name, id
        FROM rooms2
        WHERE 1=1
        """

        # Initialize params
        params_rooms = []
        params_rooms2 = []

        # Apply filters
        if city:
            query_rooms += " AND city = %s"
            query_rooms2 += " AND city = %s"
            params_rooms.append(city)
            params_rooms2.append(city)
        if room_type:
            query_rooms += " AND room_type = %s"
            params_rooms.append(room_type)
        if gender_preference:
            query_rooms += " AND gender_preference = %s"
            query_rooms2 += " AND gender_preference = %s"
            params_rooms.append(gender_preference)
            params_rooms2.append(gender_preference)

        # Combine queries using UNION ALL
        query_combined = f"{query_rooms} UNION ALL {query_rooms2}"

        # Create a cursor and execute the query
        cursor = mysql.connection.cursor()
        cursor.execute(query_combined, params_rooms + params_rooms2)
        filtered_rooms = cursor.fetchall()
        print("Filtered rooms: ", filtered_rooms)

        # Pass the filtered data to the template
        return render_template('filterd_room.html', combined_rooms=filtered_rooms)

    except Exception as e:
        # Handle exception and pass the error message to the template
        error_message = f"An error occurred: {e}"
        return render_template('filterd_room.html', error_message=error_message)

    finally:
        # Ensure cursor is closed after operation
        if cursor:
            cursor.close()




from datetime import datetime

# Function to calculate the relative time
def time_ago(post_date):
    now = datetime.now()
    diff = now - post_date

    days = diff.days
    seconds = diff.total_seconds()

    if days > 365:
        return f"{days // 365} years ago"
    elif days > 30:
        return f"{days // 30} months ago"
    elif days > 0:
        return f"{days} days ago"
    elif seconds > 3600:
        return f"{int(seconds // 3600)} hours ago"
    elif seconds > 60:
        return f"{int(seconds // 60)} minutes ago"
    else:
        return "Just now"

@app.route('/room-details/<table>/<int:room_id>', methods=['GET'])
def room_details(table, room_id):
    # Determine the correct table name
    if table == 'owner':
        table = 'rooms'
    elif table == 'informant':
        table = 'rooms2'
    else:
        return "Invalid table specified.", 400

    cursor = mysql.connection.cursor()

    # Construct the query dynamically based on the table
    query = f"SELECT * FROM {table} WHERE id = %s;"
    cursor.execute(query, (room_id,))
    room = cursor.fetchone()  # Fetch one record

    if room:
        # Identify the correct posted_date index based on the table
        if table == 'rooms':
            posted_date_index = 34  # Adjust based on your table schema
        elif table == 'rooms2':
            posted_date_index = 15  # Adjust based on your table schema
        else:
            return "Invalid table specified.", 400

        # Get the posted_date and ensure it's a datetime object
        posted_date = room[posted_date_index]
        if isinstance(posted_date, decimal.Decimal):
            posted_date = datetime.fromtimestamp(float(posted_date))
        elif isinstance(posted_date, str):
            posted_date = datetime.strptime(posted_date, "%Y-%m-%d %H:%M:%S")

        # Apply the time_ago function to the posted_date
        time_since_posted = time_ago(posted_date)

        # Render the room details template
        return render_template('room_details.html',room=room, table=table, time_since_posted=time_since_posted)

    else:
        return "Room not found", 

# Route for profile page (assuming 'profile2.html' is for viewing the profile)
@app.route('/profile2')
def profile2():

    # Ensure the user is logged in
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    username = session['username']  # Get the username from session

    # Handle POST request (profile update logic)
    

    # Handle GET request (fetch profile data from the database)
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT first_name, last_name, email, role, city, preferred_location, profile_image 
            FROM profile 
            WHERE username = %s
        """, (username,))
        profile_data = cursor.fetchone()  # Fetch a single row
        cursor.close()

        print("Fetched Profile Data:", profile_data)


        # If no data is found, use default values
        if profile_data:
            profile = {
                'first_name': profile_data[0],
                'last_name': profile_data[1],
                'email': profile_data[2],
                'role': profile_data[3],
                'city': profile_data[4],
                'preferred_location': profile_data[5],
                'profile_image': profile_data[6] if profile_data[6] else '/static/images/user2.png'  # Default image
            }
        else:
            profile = {
                'firstname': '',
                'lastname': '',
                'email': '',
                'role': '',
                'city': '',
                'preferred_location': '',
                'profile_image': '/static/images/user2.png'  # Default image
            }

    except Exception as e:
        flash('Error fetching profile data.', 'error')
        print(f"Error: {e}")
        profile = {
            'first_name': '',
            'last_name': '',
            'email': '',
            'role': '',
            'city': '',
            'preferred_location': '',
            'profile_image': '/static/images/user2.png'  # Default image
        }

    # Render the profile page with the fetched data
    return render_template('profile2.html', profile_data=profile)


#  forggeting passwrd

# Configure session timeout (e.g., 15 minutes)
app.permanent_session_lifetime = timedelta(minutes=15)

# Function: Validate Email Format
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Function: Validate Phone Number Format
def is_valid_phone(phone):
    return re.match(r"^[0-9]{10}$", phone)

# Function: Send OTP to Email
def send_otp_email(email, otp):
    try:
        smtp_server = "smtp.gmail.com"  # Update for your email provider
        smtp_port = 587
        sender_email = "your_email@gmail.com"  # Replace with your email
        sender_password = "your_email_password"  # Replace with your email password

        # Establish connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Compose and send email
        subject = "Your OTP for Password Reset"
        body = f"Your OTP is: {otp}. It will expire in 10 minutes."
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(sender_email, email, message)
        server.quit()
    except Exception as e:
        flash(f"Failed to send OTP: {str(e)}", 'error')

# Step 1: Forgot Password Page
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')

        if email and not is_valid_email(email):
            flash('Invalid email format!', 'error')
            return redirect('/forgot-password')

        if phone and not is_valid_phone(phone):
            flash('Invalid phone number format!', 'error')
            return redirect('/forgot-password')

        session.permanent = True  # Enable session timeout
        session['otp'] = str(random.randint(100000, 999999))  # Generate OTP

        if email:
            session['contact'] = email
            send_otp_email(email, session['otp'])
            flash('OTP has been sent to your email!', 'info')
        elif phone:
            session['contact'] = phone
            # Add SMS functionality here if needed
            flash('OTP has been sent to your phone number!', 'info')
        else:
            flash('Please provide an email or phone number!', 'error')
            return redirect('/forgot-password')

        return redirect('/otp')
    return render_template('forgot_password.html')

# Step 2: OTP Page
@app.route('/otp', methods=['GET', 'POST'])
def otp_page():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        if user_otp == session.get('otp'):
            flash('OTP Verified! Proceed to reset your password.', 'success')
            return redirect('/reset-password')
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return redirect('/otp')
    contact = session.get('contact')
    return render_template('otp_page.html', contact=contact)

# Step 3: Reset Password Page
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form.get('new-password')
        re_enter_password = request.form.get('re-enter-password')

        if new_password != re_enter_password:
            flash('Passwords do not match! Please try again.', 'error')
            return redirect('/reset-password')

        # Hash the password for secure storage
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        contact = session.get('contact')
        if not contact:
            flash('Session expired. Please start over.', 'error')
            return redirect('/forgot-password')

        # Update the password in the database
        cur = mysql.connection.cursor()
        if '@' in contact:  # Email
            cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, contact))
        else:  # Phone
            cur.execute("UPDATE users SET password = %s WHERE phone = %s", (hashed_password, contact))

        mysql.connection.commit()
        cur.close()

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect('/login')
    return render_template('reset_password.html')




if __name__ == "__main__":
    app.run(debug=True)
