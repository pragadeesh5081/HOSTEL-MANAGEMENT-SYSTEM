from models import db


def submit_leave(student_id, start_date, end_date, destination, reason, emergency_contact):
    db.execute(
        """INSERT INTO LeaveRequests
           (student_id, start_date, end_date, destination, reason, emergency_contact)
           VALUES (?,?,?,?,?,?)""",
        (student_id, start_date, end_date, destination, reason, emergency_contact)
    )


def get_leaves(student_id=None):
    if student_id:
        return db.fetchall(
            """SELECT l.*, u.full_name, s.registration_number
               FROM LeaveRequests l
               JOIN Students s ON l.student_id = s.student_id
               JOIN Users u    ON s.user_id    = u.user_id
               WHERE l.student_id=?
               ORDER BY l.created_at DESC""",
            (student_id,)
        )
    return db.fetchall(
        """SELECT l.*, u.full_name, s.registration_number
           FROM LeaveRequests l
           JOIN Students s ON l.student_id = s.student_id
           JOIN Users u    ON s.user_id    = u.user_id
           ORDER BY l.created_at DESC"""
    )


def get_recent_leaves(limit=5):
    return db.fetchall(
        """SELECT l.*, u.full_name, s.registration_number
           FROM LeaveRequests l
           JOIN Students s ON l.student_id = s.student_id
           JOIN Users u    ON s.user_id    = u.user_id
           ORDER BY l.created_at DESC LIMIT ?""",
        (limit,)
    )


def review_leave(leave_id, decision, admin_remarks):
    if decision not in ('Approved', 'Rejected'):
        raise ValueError("Decision must be 'Approved' or 'Rejected'.")
    db.execute(
        """UPDATE LeaveRequests
           SET status=?, admin_remarks=?, reviewed_at=datetime('now')
           WHERE leave_id=?""",
        (decision, admin_remarks, leave_id)
    )
