from models import db


def submit_complaint(student_id, title, category, description, priority='Medium'):
    db.execute(
        """INSERT INTO Complaints (student_id, title, category, description, priority)
           VALUES (?,?,?,?,?)""",
        (student_id, title, category, description, priority)
    )


def get_complaints(student_id=None):
    if student_id:
        return db.fetchall(
            """SELECT c.*, u.full_name, s.registration_number
               FROM Complaints c
               JOIN Students s ON c.student_id = s.student_id
               JOIN Users u    ON s.user_id    = u.user_id
               WHERE c.student_id=?
               ORDER BY c.created_at DESC""",
            (student_id,)
        )
    return db.fetchall(
        """SELECT c.*, u.full_name, s.registration_number
           FROM Complaints c
           JOIN Students s ON c.student_id = s.student_id
           JOIN Users u    ON s.user_id    = u.user_id
           ORDER BY c.created_at DESC"""
    )


def get_complaint_chart():
    """Returns list of {status, cnt} for dashboard charts."""
    return db.fetchall(
        "SELECT status, COUNT(*) AS cnt FROM Complaints GROUP BY status"
    )


def update_complaint_status(complaint_id, status, resolution_notes=''):
    db.execute(
        """UPDATE Complaints
           SET status=?, resolution_notes=?, updated_at=datetime('now')
           WHERE complaint_id=?""",
        (status, resolution_notes, complaint_id)
    )
