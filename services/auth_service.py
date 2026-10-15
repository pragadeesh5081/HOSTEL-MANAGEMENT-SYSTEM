from werkzeug.security import generate_password_hash, check_password_hash
from models import db


def get_user_by_email(email):
    return db.fetchone(
        "SELECT * FROM Users WHERE email = ? AND is_active = 1",
        (email,)
    )


def get_user_by_id(user_id):
    return db.fetchone(
        "SELECT * FROM Users WHERE user_id = ?",
        (user_id,)
    )


def verify_password(user, password):
    if not user:
        return False
    return check_password_hash(user['password_hash'], password)


def create_user(email, password, full_name, role='student', phone=None):
    """Create a user account. Returns the new user_id."""
    pw_hash = generate_password_hash(password)
    return db.execute(
        "INSERT INTO Users (email, password_hash, role, full_name, phone) VALUES (?, ?, ?, ?, ?)",
        (email.lower().strip(), pw_hash, role, full_name.strip(), phone)
    )


def register_student(email, password, full_name, registration_number,
                     phone=None, department=None, academic_year=None):
    """Register a new student: creates User + Student rows atomically."""
    existing = get_user_by_email(email)
    if existing:
        raise ValueError("An account with this email already exists.")

    # Check reg number uniqueness
    dup = db.fetchone(
        "SELECT 1 FROM Students WHERE registration_number = ?",
        (registration_number,)
    )
    if dup:
        raise ValueError("Registration number already in use.")

    user_id = create_user(email, password, full_name, role='student', phone=phone)
    db.execute(
        """INSERT INTO Students
           (user_id, registration_number, department, academic_year, joined_date)
           VALUES (?, ?, ?, ?, date('now'))""",
        (user_id, registration_number, department, academic_year)
    )
    return user_id


def register_admin(email, password, full_name, phone=None):
    """Register a new admin account."""
    existing = get_user_by_email(email)
    if existing:
        raise ValueError("An account with this email already exists.")
    return create_user(email, password, full_name, role='admin', phone=phone)


def change_password(user_id, new_password):
    db.execute(
        "UPDATE Users SET password_hash = ?, updated_at = datetime('now') WHERE user_id = ?",
        (generate_password_hash(new_password), user_id)
    )

