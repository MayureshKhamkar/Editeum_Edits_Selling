#ALL THE LIBRARIES 
import os
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api
import plotly.express as px
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response,send_file
from flask_mysqldb import MySQL
from datetime import datetime
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import qrcode
import io
import urllib.parse
from PIL import Image
from urllib.parse import unquote
import requests

UPI_ID = "upiid"
PAYEE_NAME = ""

# LOAD ENVIRONMENT VARIABLES
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secretkey')

# MySQL CONNECTION
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'mysql_password')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'your_db')

mysql = MySQL(app)

#CLOUDINARY CONNECTION
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME", "Your_own_cloudinaryName"),
    api_key=os.getenv("CLOUD_API_KEY", "Your_own_cloudinaryApiKey"),
    api_secret=os.getenv("CLOUD_API_SECRET", "Your_own_cloudinaryApiSecret")
)

# EXTENSIONS WHICH ARE ALLOWED TO BE UPLOADED
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_user():
    return dict(username=session.get('username'), loggedin=session.get('loggedin'))


#home page route
@app.route('/')
def home():
    return render_template('index.html')


#MAIN USER LOGIN AND REGISTER ROUTES

#user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account and check_password_hash(account['password'], password):
            session.update({'loggedin': True, 'id': account['id'], 'email': account['email'], 'username': account['username']})
            flash('Login Successful!', 'success')
            return redirect(url_for('home'))
        flash('Invalid email or password. Try again!', 'danger')
    return render_template('login.html')

#user register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already exists! Try logging in.', 'warning')
        elif not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash('Invalid email format!', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (fullname, email, username, password) VALUES (%s, %s, %s, %s)',
                           (fullname, email, username, hashed_password))
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()  # If using session-based authentication
    return redirect(url_for('login'))  # Redirect to login page



#UPLOAD SECTION


#upload edit route
@app.route('/upload_edit', methods=['GET', 'POST'])
def upload_edit():
    if request.method == 'POST':
        video_title = request.form.get('videoTitle')
        video_description = request.form.get('videoDescription')
        price = request.form.get('videoPrice')
        category = request.form.get('videoCategory', 'uncategorized')  # Default value if empty
        file = request.files.get('videoFile')

        # Ensure user is logged in
        if 'loggedin' not in session:
            flash('You must be logged in to upload!', 'danger')
            return redirect(url_for('login'))
        
        uploaded_by = session.get('id')  # Get logged-in user's ID

        if not file or file.filename == '':
            flash('No file selected!', 'danger')
            return redirect(request.url)

        if allowed_file(file.filename):
            try:
                # Upload video to Cloudinary
                upload_result = cloudinary.uploader.upload(file, resource_type="video", folder="uploaded_edits")
                file_url = upload_result.get('secure_url')

                if not file_url:
                    flash('Cloudinary upload failed!', 'danger')
                    return redirect(request.url)

                # Insert into MySQL database
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('''
                    INSERT INTO edits (title, description, file_link, price, category, uploaded_by) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (video_title, video_description, file_url, price, category, uploaded_by))
                
                mysql.connection.commit()
                cursor.close()

                flash('Video uploaded successfully!', 'success')
                return redirect(url_for('explore'))

            except Exception as e:
                flash(f'Upload failed: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Invalid file format! Only MP4, AVI, MOV, MKV allowed.', 'danger')
            return redirect(request.url)

    return render_template('uploadEdit.html')




#EXPLORE SECTION 
@app.route('/explore')
def explore():
    search_query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search_query:
        cursor.execute("SELECT * FROM edits WHERE title LIKE %s", ('%' + search_query + '%',))
    else:
        cursor.execute("SELECT * FROM edits")

    videos = cursor.fetchall()

    purchased_ids = set()
    if 'loggedin' in session:
        user_id = session['id']
        cursor.execute("SELECT video_id FROM purchases WHERE user_id = %s", (user_id,))
        purchased_ids = set(row['video_id'] for row in cursor.fetchall())

    # Add flag to each video
    for video in videos:
        video['already_purchased'] = video['id'] in purchased_ids

    cursor.close()
    return render_template('explore.html', videos=videos, search_query=search_query)


#ADMIN SECTION

#admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    session.clear()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admin WHERE email = %s', (email,))
        admin = cursor.fetchone()

        # Fix password verification
        if admin and admin['password'] == password:  # Only if passwords are stored as plain text
 # Use this if passwords are hashed
            session['admin_loggedin'] = True
            session['admin_id'] = admin['id']
            session['admin_email'] = admin['email']
            flash('Admin Login Successful!', 'success')
            return redirect(url_for('admin_dashboard'))

            flash('Invalid email or password. Try again!', 'danger')

    return render_template('adminLogin.html')

#admin dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_loggedin' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('admin_login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()['total_users'] or 0

    cursor.execute("SELECT COUNT(*) AS total_videos FROM edits")
    total_videos = cursor.fetchone()['total_videos'] or 0

    cursor.execute("SELECT SUM(price) AS total_sales FROM edits")  # Corrected line
    total_sales = cursor.fetchone()['total_sales'] or 0

    return render_template('adminDashboard.html', total_users=total_users, total_videos=total_videos, total_sales=total_sales)

#this is dashboard chart route it shows website details to admin through charts
@app.route('/admin_dashboard_chart')
def admin_dashboard_chart():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()['total_users'] or 0

    cursor.execute("SELECT COUNT(*) AS total_videos FROM edits")
    total_videos = cursor.fetchone()['total_videos'] or 0

    cursor.execute("SELECT SUM(price) AS total_sales FROM edits")
    total_sales = cursor.fetchone()['total_sales'] or 0

    # Send JSON response
    return jsonify({
        "labels": ["Total Users", "Total Edits", "Total Sales"],
        "data": [total_users, total_videos, total_sales]
    })

#admin count videos
@app.route('/admin_videos')
def admin_videos():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor
    cursor.execute("""
        SELECT e.id, e.title, e.description, e.file_link, e.price, u.username AS uploader_name
        FROM edits e
        JOIN users u ON e.uploaded_by = u.id
    """)
    videos = cursor.fetchall()
    cursor.close()
    return render_template("adminVideos.html", videos=videos)

#admin register count
@app.route('/admin/users')
def admin_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, fullname, email, username FROM users")
    users = cursor.fetchall()
    cursor.close()

    return render_template('adminUsers.html', users=users)


#admin can delete the user by its id
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        mysql.connection.commit()
    except Exception as e:
        print(f"Error deleting user: {e}")
    finally:
        cursor.close()
    return redirect(url_for('admin_users'))

#admin can delete videos through this route
@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM edits WHERE id = %s", (video_id,))
        video = cursor.fetchone()

        if not video:
            flash("Video not found!", "danger")
            return redirect(url_for('admin_videos'))

        cursor.execute("DELETE FROM edits WHERE id = %s", (video_id,))
        mysql.connection.commit()
        cursor.close()

        flash("Video deleted successfully!", "success")

    except Exception as e:
        flash(f"Error deleting video: {str(e)}", "danger")

    return redirect(url_for('admin_videos'))




#this is transaction route by which you can check the purchases of the edits


#admin logout route
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_loggedin', None)
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    flash('Admin logged out successfully!', 'success')
    return redirect(url_for('admin_login'))



#BLOG SECTION
#Blog route (fetching blogs from database)
@app.route('/blogs')
def blogs():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM blogs ORDER BY created_at DESC")
    blogs = cursor.fetchall()
    cursor.close()
    return render_template('blogs.html', blogs=blogs)

#uploading blogs from admin panel
@app.route('/upload_blog', methods=['GET', 'POST'])
def upload_blog():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        additional_content = request.form.get('additional_content', '')
        image = request.files.get('image')

        try:
            image_url = None
            if image:
                upload_result = cloudinary.uploader.upload(image, folder="upload_blogs")
                image_url = upload_result['secure_url']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute(
                "INSERT INTO blogs (title, content, additional_content, image_url, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (title, content, additional_content, image_url)
            )
            mysql.connection.commit()
            cursor.close()

            flash("Blog uploaded successfully!", "success")
            return redirect(url_for('upload_blog'))

        except Exception as e:
            flash(f"Error uploading blog: {str(e)}", "danger")

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, title, created_at FROM blogs ORDER BY created_at DESC")
        blogs = cursor.fetchall()
        cursor.close()
    except Exception as e:
        blogs = []
        flash("Error fetching blogs: " + str(e), "danger")

    return render_template("upload_blog.html", blogs=blogs)


#delete the blog through adminpanel and also backend with delete button
@app.route('/admin/delete_blog/<int:blog_id>', methods=['POST'])
def delete_blog(blog_id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
        blog = cursor.fetchone()
        if not blog:
            return jsonify({"success": False, "message": "Blog not found"}), 404

        cursor.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Blog deleted successfully!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/admin_transactions')
def admin_transactions():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT p.id, u.fullname, e.title, p.price, p.purchase_date
        FROM purchases p
        JOIN users u ON p.user_id = u.id
        JOIN edits e ON p.video_id = e.id
        ORDER BY p.purchase_date DESC
    """)
    transactions = cursor.fetchall()
    cursor.close()
    return render_template('adminTransactions.html', transactions=transactions)

#REVIEW ROUTE
# User Review Route
@app.route('/review', methods=['GET', 'POST'])
def review():
    user_logged_in = 'loggedin' in session

    if request.method == 'POST':
        if not user_logged_in:
            flash("You must be logged in to submit a review.", "danger")
            return redirect(url_for('login'))

        user_id = session['id']
        username = session['username']
        review_text = request.form.get('reviewText')
        star_rating = request.form.get('starRating', 5)
        avatar_url = session.get('avatar_url', '')

        if not review_text.strip():
            flash("Review text cannot be empty.", "warning")
            return redirect(url_for('review'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO reviews (user_id, username, comment, review_text, avatar_url, star_rating, likes, dislikes, date)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 0, NOW())
        """, (user_id, username, review_text, review_text, avatar_url, star_rating))
        mysql.connection.commit()
        cursor.close()

        flash("Review submitted successfully!", "success")
        return redirect(url_for('review'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM reviews ORDER BY date DESC")
    reviews = cursor.fetchall()
    cursor.close()

    return render_template('review.html', reviews=reviews, loggedin=user_logged_in)


# Like/Dislike Route
@app.route('/review/<int:review_id>/engage', methods=['POST'])
def review_engage(review_id):
    if 'loggedin' not in session:
        return jsonify({"success": False, "message": "Login required"}), 401

    action = request.json.get('action')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if action == 'like':
        cursor.execute("UPDATE reviews SET likes = likes + 1 WHERE id = %s", (review_id,))
    elif action == 'dislike':
        cursor.execute("UPDATE reviews SET dislikes = dislikes + 1 WHERE id = %s", (review_id,))
    
    mysql.connection.commit()
    cursor.close()

    return jsonify({"success": True, "message": f"Review {action}d successfully"})


# Delete Review Route
@app.route('/review/delete/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if 'loggedin' not in session and 'admin_loggedin' not in session:
        flash("Login required!", "danger")
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT user_id FROM reviews WHERE id = %s", (review_id,))
    review = cursor.fetchone()

    if review and ((session.get('id') == review['user_id']) or session.get('admin_loggedin')):
        cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        mysql.connection.commit()
        flash("Review deleted successfully!", "success")
    else:
        flash("Unauthorized action!", "danger")

    cursor.close()
    return redirect(url_for('review'))


# Admin Review Management Route
@app.route('/admin/reviews', methods=['GET', 'POST'])
def admin_reviews():
    if 'admin_loggedin' not in session:
        flash('Please log in as admin first.', 'danger')
        return redirect(url_for('admin_login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        review_text = request.form.get('review_text', '').strip()

        if review_text:
            cursor.execute('SELECT username FROM admin WHERE id = %s', (session['admin_id'],))
            admin = cursor.fetchone()

            if admin:
                admin_username = admin['username']

                # Insert admin review (no user_id, so pass NULL)
                cursor.execute("""
                    INSERT INTO reviews (user_id, username, comment, review_text, avatar_url, star_rating, likes, dislikes, date)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 0, NOW())
                """, (None, admin_username, review_text, review_text, "", 5))
                mysql.connection.commit()
                flash('Admin review posted successfully!', 'success')
            else:
                flash('Admin username not found.', 'danger')
        else:
            flash('Review text cannot be empty.', 'warning')

        return redirect(url_for('admin_reviews'))

    cursor.execute("SELECT * FROM reviews ORDER BY date DESC")
    reviews = cursor.fetchall()
    cursor.close()

    return render_template('admin_reviews.html', reviews=reviews)


@app.route('/admin/reviews/delete/<int:review_id>', methods=['POST'])
def admin_delete_review(review_id):
    # Ensure admin is logged in
    if 'admin_loggedin' not in session:
        flash('Please log in as admin first.', 'danger')
        return redirect(url_for('admin_login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Delete review regardless of who posted it (admin or user)
    cursor.execute('DELETE FROM reviews WHERE id = %s', (review_id,))
    mysql.connection.commit()

    flash('Review deleted successfully.', 'success')
    return redirect(url_for('admin_reviews'))



#CONTACT ROUTE
@app.route('/contact')
def contact():
    return render_template('contact.html')

#VIEWPROFILE ROUTE
@app.route('/viewProfile')
def view_profile():
    return render_template('viewProfile.html')

#ACTIVITY ROUTE
@app.route('/activity')
def activity():
    return render_template('activity.html')



@app.route('/create_order', methods=['POST'])
def create_order():
    if 'loggedin' not in session:
        flash("Please log in to make a purchase.", "warning")
        return redirect(url_for('login'))

    video_id = request.form.get('video_id')
    user_id = session["id"]

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM purchases WHERE user_id = %s AND video_id = %s", (user_id, video_id))
    if cursor.fetchone():
        flash("You've already purchased this video.", "warning")
        return redirect(url_for('purchased_videos'))

    cursor.execute("SELECT * FROM edits WHERE id = %s", (video_id,))
    video = cursor.fetchone()
    cursor.close()

    if not video:
        return "Video not found", 404

    amount = str(video['price'])
    upi_link = (
        f"upi://pay?pa={UPI_ID}&pn={PAYEE_NAME}&am={amount}&cu=INR"
        f"&tn=Purchase%20{video['title']}"
    )

    session['pending_video_id'] = video_id
    session['pending_price'] = amount
    session['upi_link'] = upi_link

    return render_template('confirm_payment.html', upi_link=upi_link, video=video)

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    if 'loggedin' not in session:
        flash("Please log in to confirm payment.", "danger")
        return redirect(url_for('login'))

    user_id = session.get("id")
    video_id = request.form.get("video_id")
    price = request.form.get("price")

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM purchases WHERE user_id = %s AND video_id = %s", (user_id, video_id))
    if cursor.fetchone():
        flash("You've already purchased this video.", "info")
        cursor.close()
        return redirect(url_for("purchased_videos"))

    cursor.execute(
        "INSERT INTO purchases (user_id, video_id, price) VALUES (%s, %s, %s)",
        (user_id, video_id, price)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Payment confirmed! Video added to your purchases.", "success")
    return redirect(url_for("purchased_videos"))

@app.route('/payment_success', methods=['POST'])
def payment_success():
    if 'pending_video_id' not in session or 'pending_price' not in session:
        flash("Session expired or invalid payment action.", "danger")
        return redirect(url_for("explore"))

    user_id = session.get("id")
    video_id = session.pop("pending_video_id", None)
    price = session.pop("pending_price", None)

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM purchases WHERE user_id = %s AND video_id = %s", (user_id, video_id))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO purchases (user_id, video_id, price) VALUES (%s, %s, %s)",
            (user_id, video_id, price)
        )
        mysql.connection.commit()
    cursor.close()

    return redirect(url_for("purchased_videos", payment_success="true"))

@app.route('/generate_qr')
def generate_qr():
    try:
        upi_url = request.args.get('upi_url')
        if not upi_url:
            raise ValueError("Missing UPI URL")

        decoded_url = unquote(upi_url)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(decoded_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print("QR Generation Error:", e)
        fallback = io.BytesIO()
        fallback_img = Image.new("RGB", (200, 200), color="gray")
        fallback_img.save(fallback, format='PNG')
        fallback.seek(0)
        return send_file(fallback, mimetype='image/png')

@app.route('/purchased_videos')
def purchased_videos():
    if 'loggedin' not in session:
        flash("Please log in to view your purchases.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("id")
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT e.title, e.thumbnail_url, e.file_link, p.purchase_date, p.price
        FROM purchases p
        JOIN edits e ON p.video_id = e.id
        WHERE p.user_id = %s
        ORDER BY p.purchase_date DESC
    """, (user_id,))
    videos = cursor.fetchall()
    cursor.close()

    # Process file_link for download
    for video in videos:
        if video['file_link']:
            filename = video['title'].replace(' ', '_') + '.mp4'
            video['download_url'] = video['file_link'] + f'?fl_attachment={filename}'
        else:
            video['download_url'] = '#'

    payment_success = request.args.get('payment_success') == "true"
    return render_template("Purchased_videos.html", videos=videos, payment_success=payment_success)

@app.route('/upi_callback', methods=['POST'])
def upi_callback():
    # This is for future use with UPI APIs that POST transaction status
    data = request.get_json()
    print("Received UPI callback:", data)

    # Parse transaction data here and validate
    # Example:
    transaction_id = data.get('txnId')
    status = data.get('status')
    user_id = data.get('user_id')
    video_id = data.get('video_id')

    if status == "SUCCESS":
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT IGNORE INTO purchases (user_id, video_id, price) VALUES (%s, %s, %s)",
            (user_id, video_id, data.get('amount'))
        )
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Purchase recorded"}), 200

    return jsonify({"message": "Payment not successful"}), 400
 

@app.route('/download/<filename>')
def download_video(filename):
    video_path = os.path.join('static', 'videos', filename)
    return send_file(video_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)


