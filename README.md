
# 🎬 Editeum – Edit Selling & Skill Showcase Platform

**Editeum** is a creative platform designed for video editors and digital artists to showcase and sell their edits, while users can explore, purchase, and review the content. It offers a dual interface for users and administrators, built using Flask and HTML/CSS/JS, ideal for portfolio-level deployment or as a final-year academic project.

---

## 📂 Project Structure Overview

```
Editeum/
├── static/                  # Contains CSS, JavaScript, and media files
├── templates/               # Jinja2 HTML Templates (Login, Register, Admin Pages, etc.)
│   ├── login.html
│   ├── register.html
│   ├── uploadEdit.html
│   ├── viewProfile.html
│   ├── adminDashboard.html
│   ├── Purchased_videos.html
│   └── ...
├── videos/                  # Local videos (e.g. banners, sample edits)
├── .env                     # Environment configuration
├── app.py                   # Main Flask backend
└── README.md                # Project documentation (this file)
```

---

## 🔧 Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python Flask
- **Templating**: Jinja2 (Flask)
- **Database**: SQLite (via Flask SQLAlchemy or raw connection)
- **Environment**: `.env` for configs
- **IDE/Editor**: Visual Studio Code

---

## ✨ Key Features

### 👤 User Functionalities
- User Registration and Login
- Upload/Edit Showcase Videos
- View and Edit Profile
- Explore Available Edits
- Purchase and Download Edits
- Review Purchased Content

### 🔐 Admin Functionalities
- Admin Login Portal
- Dashboard to Manage Users
- Review Uploaded Edits
- Handle Transactions
- Manage Blogs and Contact Entries

---

## 🚀 Getting Started (Local Setup)


### 2. Set Up Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install flask python-dotenv
```

### 4. Configure .env File

Create a `.env` file in the root:

```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///yourdb.db
```

### 5. Run the Application

```bash
flask run
```

Visit `http://localhost:5000` in your browser.

---

## 🖼️ Media Assets & Screenshots

The `videos/` folder contains video banners like:

- `editeum banner.mp4`
- `banner 2.mp4`

These can be used as homepage video backgrounds or editor previews.

The `static/` folder contains:

- Stylesheets for layout and responsiveness
- JavaScript files for interactivity

---

## 🧩 Template Pages (from /templates)

| Template File          | Purpose                        |
|------------------------|--------------------------------|
| `login.html`           | User login page                |
| `register.html`        | User registration page         |
| `uploadEdit.html`      | Upload form for editors        |
| `viewProfile.html`     | Profile view with edit history |
| `adminDashboard.html`  | Admin control panel            |
| `Purchased_videos.html`| Purchased edit viewing         |
| `blogs.html`           | Blog section (editable content)|
| `checkout.html`        | Simulated payment/checkout     |

---

## 💡 Future Enhancements

- Online Payment Gateway Integration (Google pay Scanner)
- Real-Time Notifications
- Comment System
- Edit Categories & Filters
- Search Functionality

---

## 📜 License

This project is created for academic purposes and is open to learning use. Commercial use requires permission from the developer.

---

## 👨‍💻 Developed By

**Your Name**  
TYBBA(CA) – Final Year Project  
Savitribai Phule Pune University  
April 2025

---
