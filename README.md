# 🏫 Hostel Management System (HMS)

A **premium, full-stack Hostel Management System** built with Python Flask and Microsoft SQL Server. Features a modern animated UI with glassmorphism login, animated dashboards, real-time statistics from the database, and responsive layouts.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 🔐 Authentication | Secure login, registration, session management, bcrypt password hashing |
| 👥 Student Management | Admin-created or self-registered student accounts with profile management |
| 🏠 Room Management | Visual room cards with animated occupancy bars, add/edit/filter rooms |
| 🔑 Room Allocations | Allocate rooms to students with capacity enforcement, vacate rooms |
| 🔄 Room Change Requests | Students request room changes; admin approves/rejects |
| 📅 Leave Management | Submit leave applications; admin reviews with remarks |
| 📋 Complaint Management | Submit complaints by category/priority; admin updates status |
| 📢 Announcements | Admin posts announcements with category, expiry; students view live |
| 📊 Reports & Analytics | Charts for room occupancy and complaint status from live DB data |
| 🎨 Premium UI | Glassmorphism login, animated counters, sidebar, toast notifications |

---

## 🛠 Technology Stack

- **Backend:** Python 3.10+, Flask 3.0
- **Database:** Microsoft SQL Server (pyodbc)
- **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript
- **Icons:** Bootstrap Icons
- **Charts:** Chart.js

---

## 📋 Prerequisites

Install the following before proceeding:

1. **Python 3.10+** — [python.org](https://www.python.org/downloads/)
2. **Microsoft SQL Server 2019+** (Express edition is fine) — [microsoft.com](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
3. **SQL Server Management Studio (SSMS)** — [download here](https://aka.ms/ssmsfullsetup)
4. **ODBC Driver 17 for SQL Server** — [download here](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
5. **Git** (optional) — [git-scm.com](https://git-scm.com/)
6. **Visual Studio Code** — [code.visualstudio.com](https://code.visualstudio.com/)

---

## 🚀 Setup Instructions

### Step 1 — Clone or Download the Project

```bash
# If using Git
git clone <your-repo-url>
cd "HOSTEL MANAGEMENT SYSTEM"

# Or open the folder directly in VS Code
```

### Step 2 — Create a Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure SQL Server

1. Open **SQL Server Management Studio (SSMS)**
2. Connect to your SQL Server instance (e.g. `localhost` or `.\SQLEXPRESS`)
3. Ensure SQL Server is running

**Check your SQL Server instance name:**
```bash
# PowerShell — lists running SQL Server services
Get-Service -Name "MSSQL*"
```

Common instance names:
- `localhost` (default instance)
- `localhost\SQLEXPRESS` (Express edition)
- `.\MSSQLSERVER`

### Step 5 — Create the Database

Open SSMS → New Query → Run the SQL script:

```bash
# Or run via sqlcmd:
sqlcmd -S localhost -E -i database.sql

# For named instances:
sqlcmd -S localhost\SQLEXPRESS -E -i database.sql
```

This creates the `HostelManagementDB` database with all tables, indexes, and sample room data.

### Step 6 — Configure Environment Variables

Copy the example file and fill in your values:

```bash
copy .env.example .env
```

Open `.env` and set your values:

```ini
SECRET_KEY=your-very-long-random-secret-key-here
DB_SERVER=localhost
DB_NAME=HostelManagementDB
DB_DRIVER=ODBC Driver 17 for SQL Server

# Windows Authentication (leave empty to use Windows Auth — recommended)
DB_USER=
DB_PASSWORD=

# SQL Server Authentication (fill in if not using Windows Auth)
# DB_USER=sa
# DB_PASSWORD=your-sql-password
```

> **Tip:** Generate a secret key:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### Step 7 — Create the First Administrator

Run the secure admin creation script:

```bash
python create_admin.py
```

Follow the prompts:
```
=== Hostel Management System — Create Admin ===
Admin full name: Dr. Admin
Admin email:     admin@hostel.edu
Phone (optional): 9876543210
Password:        ••••••••
Confirm password: ••••••••

✓ Admin account created for 'Dr. Admin' (admin@hostel.edu)
  You can now log in at http://localhost:5000/login
```

### Step 8 — Start the Flask Application

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Step 9 — Access the Application

Open your browser and visit:

```
http://localhost:5000
```

- **Admin login:** Use the credentials from Step 7
- **Student login:** Create a student account via the admin panel or use `/register`

---

## 👤 Default Workflow

### First-time Admin Setup
1. Log in as admin
2. Go to **Rooms** → Add hostel rooms
3. Go to **Students** → Add students (or students can self-register)
4. Go to **Allocations** → Allocate rooms to students

### Student Flow
1. Register at `/register` or get account from admin
2. Log in → View dashboard
3. See room allocation, submit leave applications, raise complaints
4. View announcements posted by admin

---

## 🗂 Project Structure

```
HOSTEL MANAGEMENT SYSTEM/
├── app.py                    # Flask entry point
├── config.py                 # Configuration from .env
├── create_admin.py           # Admin bootstrap script
├── database.sql              # SQL Server schema + sample data
├── requirements.txt          # Python dependencies
├── .env                      # Local environment variables (DO NOT COMMIT)
├── .env.example              # Template for .env
├── README.md                 # This file
│
├── models/
│   ├── __init__.py
│   └── db.py                 # Database connection + helper functions
│
├── services/
│   ├── auth_service.py       # Authentication, password hashing
│   ├── student_service.py    # Student CRUD operations
│   ├── room_service.py       # Room + allocation + change requests
│   ├── leave_service.py      # Leave application management
│   ├── complaint_service.py  # Complaint management
│   └── announcement_service.py  # Announcement CRUD
│
├── routes/
│   ├── decorators.py         # @login_required, @admin_required, @student_required
│   ├── auth_routes.py        # Login, register, logout
│   ├── student_routes.py     # All student-facing pages
│   └── admin_routes.py       # All admin-facing pages
│
├── templates/
│   ├── layouts/
│   │   ├── base.html         # Base HTML with CSS/JS includes
│   │   └── dashboard.html    # Sidebar + topbar layout
│   ├── auth/
│   │   ├── login.html        # Glassmorphism animated login
│   │   └── register.html     # Student registration
│   ├── student/              # All student pages
│   └── admin/                # All admin pages
│
├── static/
│   ├── css/
│   │   ├── animations.css    # Complete animation & design system
│   │   └── main.css          # Global styles
│   └── js/
│       └── hms.js            # Sidebar, counters, toasts, search, etc.
│
└── tests/
    └── test_hms.py           # Automated test suite (pytest)
```

---

## 🧪 Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
python -m pytest tests/ -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

Tests use `unittest.mock` — no live database connection required.

---

## 🔧 Common Errors and Solutions

### ❌ `pyodbc.InterfaceError: ('IM002', ...)`
**Cause:** ODBC Driver not found.  
**Fix:** Download and install **ODBC Driver 17 for SQL Server** from Microsoft, then update `DB_DRIVER` in `.env`.

---

### ❌ `Login timeout expired` or `Cannot open server`
**Cause:** SQL Server not running or wrong server name.  
**Fix:**
1. Start SQL Server: `Start-Service MSSQLSERVER` (PowerShell as admin)
2. Check instance name: `DB_SERVER=localhost\SQLEXPRESS` for Express edition

---

### ❌ `Login failed for user`
**Cause:** Wrong credentials or SQL Server authentication not enabled.  
**Fix for Windows Auth:** Leave `DB_USER` and `DB_PASSWORD` empty in `.env`.  
**Fix for SQL Auth:** Enable "SQL Server and Windows Authentication Mode" in SSMS → Server Properties → Security.

---

### ❌ `Cannot connect to HostelManagementDB`
**Cause:** Database not created yet.  
**Fix:** Run `database.sql` in SSMS or via sqlcmd (Step 5).

---

### ❌ `Flask: No module named 'flask'`
**Cause:** Virtual environment not activated.  
**Fix:** Run `venv\Scripts\activate` (Windows) first.

---

### ❌ Student dashboard shows "Student profile not found"
**Cause:** User account created without a corresponding `Students` row.  
**Fix:** Admin should go to Students → Add Student (which creates both the user and student profile atomically).

---

## 🔒 Security Notes

- Passwords are hashed with `Werkzeug`'s `generate_password_hash` (PBKDF2-SHA256)
- Sessions are HTTP-only cookies with SameSite=Lax
- All SQL queries use parameterized statements (no string concatenation)
- Admin routes are protected by `@admin_required` decorator
- Students can only access their own data (filtered by `student_id` from session)
- Never commit `.env` to source control

---

## 📝 License

This project is created for academic purposes. Feel free to use and modify it.
