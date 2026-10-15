from models import db


def get_student_by_user_id(user_id):
    return db.fetchone(
        """SELECT s.*, u.email, u.full_name, u.phone, u.is_active
           FROM Students s
           JOIN Users u ON s.user_id = u.user_id
           WHERE s.user_id = ?""",
        (user_id,)
    )


def get_student_by_id(student_id):
    return db.fetchone(
        """SELECT s.*, u.email, u.full_name, u.phone
           FROM Students s
           JOIN Users u ON s.user_id = u.user_id
           WHERE s.student_id = ?""",
        (student_id,)
    )


def get_all_students():
    return db.fetchall(
        """SELECT s.*, u.email, u.full_name, u.phone
           FROM Students s
           JOIN Users u ON s.user_id = u.user_id
           ORDER BY u.full_name"""
    )


def create_student_by_admin(email, password, full_name, registration_number,
                             phone=None, department=None, academic_year=None,
                             guardian_name=None, guardian_phone=None, address=None):
    from services.auth_service import create_user
    existing = db.fetchone("SELECT 1 FROM Users WHERE email = ?", (email.lower().strip(),))
    if existing:
        raise ValueError("Email already in use.")
    dup = db.fetchone("SELECT 1 FROM Students WHERE registration_number = ?", (registration_number,))
    if dup:
        raise ValueError("Registration number already in use.")
    user_id = create_user(email, password, full_name, role='student', phone=phone)
    db.execute(
        """INSERT INTO Students
           (user_id, registration_number, department, academic_year,
            guardian_name, guardian_phone, address, joined_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, date('now'))""",
        (user_id, registration_number, department, academic_year,
         guardian_name, guardian_phone, address)
    )


def update_student_profile(student_id, department, academic_year,
                            guardian_name, guardian_phone, address,
                            full_name, phone, registration_number=None):
    if registration_number:
        reg_clean = registration_number.strip()
        dup = db.fetchone(
            "SELECT 1 FROM Students WHERE registration_number = ? AND student_id != ?",
            (reg_clean, student_id)
        )
        if dup:
            raise ValueError(f"Registration number '{reg_clean}' is already in use by another student.")
        db.execute(
            """UPDATE Students
               SET department=?, academic_year=?, guardian_name=?,
                   guardian_phone=?, address=?, registration_number=?
               WHERE student_id=?""",
            (department, academic_year, guardian_name, guardian_phone, address, reg_clean, student_id)
        )
    else:
        db.execute(
            """UPDATE Students
               SET department=?, academic_year=?, guardian_name=?,
                   guardian_phone=?, address=?
               WHERE student_id=?""",
            (department, academic_year, guardian_name, guardian_phone, address, student_id)
        )
    student = get_student_by_id(student_id)
    if student:
        db.execute(
            "UPDATE Users SET full_name=?, phone=?, updated_at=datetime('now') WHERE user_id=?",
            (full_name, phone, student['user_id'])
        )



def toggle_student_status(student_id):
    student = db.fetchone(
        "SELECT account_status, user_id FROM Students WHERE student_id = ?",
        (student_id,)
    )
    if not student:
        raise ValueError("Student not found.")
    new_status = 'inactive' if student['account_status'] == 'active' else 'active'
    db.execute(
        "UPDATE Students SET account_status=? WHERE student_id=?",
        (new_status, student_id)
    )
    db.execute(
        "UPDATE Users SET is_active=?, updated_at=datetime('now') WHERE user_id=?",
        (1 if new_status == 'active' else 0, student['user_id'])
    )
