from models import db


def get_announcements(active_only=True):
    if active_only:
        return db.fetchall(
            """SELECT a.*, u.full_name AS created_by_name
               FROM Announcements a
               JOIN Users u ON a.created_by = u.user_id
               WHERE a.is_active=1
                 AND (a.expiry_date IS NULL OR a.expiry_date >= date('now'))
               ORDER BY a.created_at DESC"""
        )
    return db.fetchall(
        """SELECT a.*, u.full_name AS created_by_name
           FROM Announcements a
           JOIN Users u ON a.created_by = u.user_id
           ORDER BY a.created_at DESC"""
    )


def get_announcement_by_id(ann_id):
    return db.fetchone(
        "SELECT * FROM Announcements WHERE announcement_id=?",
        (ann_id,)
    )


def create_announcement(title, message, category, created_by, expiry_date=None):
    db.execute(
        """INSERT INTO Announcements (title, message, category, created_by, expiry_date)
           VALUES (?,?,?,?,?)""",
        (title, message, category, created_by, expiry_date or None)
    )


def update_announcement(ann_id, title, message, category, expiry_date=None):
    db.execute(
        """UPDATE Announcements
           SET title=?, message=?, category=?, expiry_date=?, updated_at=datetime('now')
           WHERE announcement_id=?""",
        (title, message, category, expiry_date or None, ann_id)
    )


def delete_announcement(ann_id):
    db.execute(
        "DELETE FROM Announcements WHERE announcement_id=?",
        (ann_id,)
    )
