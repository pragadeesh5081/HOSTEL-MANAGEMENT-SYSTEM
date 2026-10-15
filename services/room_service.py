from models import db


# ── Rooms ──────────────────────────────────────────────────

def get_all_rooms():
    return db.fetchall(
        "SELECT * FROM Rooms ORDER BY floor, room_number"
    )


def get_room_stats():
    total              = db.fetchone("SELECT COUNT(*) AS cnt FROM Rooms")['cnt']
    available          = db.fetchone("SELECT COUNT(*) AS cnt FROM Rooms WHERE status='Available'")['cnt']
    full               = db.fetchone("SELECT COUNT(*) AS cnt FROM Rooms WHERE status='Full'")['cnt']
    occupied_beds      = db.fetchone("SELECT COALESCE(SUM(occupied_count), 0) AS cnt FROM Rooms")['cnt']
    total_capacity     = db.fetchone("SELECT COALESCE(SUM(capacity), 0) AS cnt FROM Rooms")['cnt']
    active_allocations = db.fetchone("SELECT COUNT(*) AS cnt FROM Allocations WHERE status='Active'")['cnt']
    return {
        'total': total,
        'available': available,
        'full_rooms': full,
        'occupied_beds': occupied_beds,
        'total_capacity': total_capacity,
        'active_allocations': active_allocations
    }


def add_room(room_number, floor, room_type, capacity):
    if db.fetchone("SELECT 1 FROM Rooms WHERE room_number=?", (room_number,)):
        raise ValueError(f"Room {room_number} already exists.")
    db.execute(
        "INSERT INTO Rooms (room_number, floor, room_type, capacity) VALUES (?,?,?,?)",
        (room_number, int(floor), room_type, int(capacity))
    )


def update_room(room_id, room_number, floor, room_type, capacity, status):
    db.execute(
        """UPDATE Rooms
           SET room_number=?, floor=?, room_type=?, capacity=?, status=?,
               updated_at=datetime('now')
           WHERE room_id=?""",
        (room_number, int(floor), room_type, int(capacity), status, room_id)
    )


# ── Allocations ────────────────────────────────────────────

def get_all_allocations():
    return db.fetchall(
        """SELECT a.*, s.registration_number, u.full_name,
                  r.room_number, r.floor, r.room_type
           FROM Allocations a
           JOIN Students s ON a.student_id = s.student_id
           JOIN Users u    ON s.user_id    = u.user_id
           JOIN Rooms r    ON a.room_id    = r.room_id
           ORDER BY a.created_at DESC"""
    )


def get_active_allocation(student_id):
    return db.fetchone(
        """SELECT a.*, r.room_number, r.floor, r.room_type,
                  r.capacity, r.occupied_count
           FROM Allocations a
           JOIN Rooms r ON a.room_id = r.room_id
           WHERE a.student_id=? AND a.status='Active'
           ORDER BY a.allocation_id DESC""",
        (student_id,)
    )


def allocate_room(student_id, room_id):
    """Allocate a room to a student. Raises ValueError on failure."""
    # Already has active allocation?
    existing = db.fetchone(
        "SELECT 1 FROM Allocations WHERE student_id=? AND status='Active'",
        (student_id,)
    )
    if existing:
        raise ValueError("Student already has an active room allocation.")

    room = db.fetchone("SELECT * FROM Rooms WHERE room_id=?", (room_id,))
    if not room:
        raise ValueError("Room not found.")
    if room['occupied_count'] >= room['capacity']:
        raise ValueError("Room is at full capacity.")
    if room['status'] not in ('Available',):
        raise ValueError(f"Room is not available (status: {room['status']}).")

    db.execute(
        """INSERT INTO Allocations (student_id, room_id, allocation_date)
           VALUES (?, ?, date('now'))""",
        (student_id, room_id)
    )
    actual_count = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM Allocations WHERE room_id=? AND status='Active'",
        (room_id,)
    )['cnt']
    new_status = 'Full' if actual_count >= room['capacity'] else 'Available'
    db.execute(
        "UPDATE Rooms SET occupied_count=?, status=?, updated_at=datetime('now') WHERE room_id=?",
        (actual_count, new_status, room_id)
    )


def vacate_room(allocation_id):
    alloc = db.fetchone(
        "SELECT * FROM Allocations WHERE allocation_id=? AND status='Active'",
        (allocation_id,)
    )
    if not alloc:
        raise ValueError("Active allocation not found.")
    db.execute(
        "UPDATE Allocations SET status='Vacated', vacate_date=date('now') WHERE allocation_id=?",
        (allocation_id,)
    )
    room = db.fetchone("SELECT * FROM Rooms WHERE room_id=?", (alloc['room_id'],))
    actual_count = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM Allocations WHERE room_id=? AND status='Active'",
        (alloc['room_id'],)
    )['cnt']
    new_status = 'Full' if actual_count >= room['capacity'] else 'Available'
    db.execute(
        "UPDATE Rooms SET occupied_count=?, status=?, updated_at=datetime('now') WHERE room_id=?",
        (actual_count, new_status, alloc['room_id'])
    )



# ── Room Change Requests ───────────────────────────────────

def get_change_requests(student_id=None):
    if student_id:
        return db.fetchall(
            """SELECT rcr.*, rr.room_number AS requested_room, cr.room_number AS current_room
               FROM RoomChangeRequests rcr
               JOIN Rooms rr ON rcr.requested_room_id = rr.room_id
               JOIN Rooms cr ON rcr.current_room_id   = cr.room_id
               WHERE rcr.student_id=?
               ORDER BY rcr.requested_at DESC""",
            (student_id,)
        )
    return db.fetchall(
        """SELECT rcr.*, rr.room_number AS requested_room, cr.room_number AS current_room,
                  u.full_name, s.registration_number
           FROM RoomChangeRequests rcr
           JOIN Rooms rr   ON rcr.requested_room_id = rr.room_id
           JOIN Rooms cr   ON rcr.current_room_id   = cr.room_id
           JOIN Students s ON rcr.student_id        = s.student_id
           JOIN Users u    ON s.user_id             = u.user_id
           ORDER BY rcr.requested_at DESC"""
    )


def submit_change_request(student_id, current_room_id, requested_room_id, reason):
    pending = db.fetchone(
        "SELECT 1 FROM RoomChangeRequests WHERE student_id=? AND status='Pending'",
        (student_id,)
    )
    if pending:
        raise ValueError("You already have a pending room change request.")
    db.execute(
        """INSERT INTO RoomChangeRequests
           (student_id, current_room_id, requested_room_id, reason)
           VALUES (?,?,?,?)""",
        (student_id, current_room_id, requested_room_id, reason)
    )


def review_change_request(request_id, decision, reviewed_by):
    req = db.fetchone(
        "SELECT * FROM RoomChangeRequests WHERE request_id=? AND status='Pending'",
        (request_id,)
    )
    if not req:
        raise ValueError("Pending request not found.")
    db.execute(
        """UPDATE RoomChangeRequests
           SET status=?, reviewed_by=?, reviewed_at=datetime('now')
           WHERE request_id=?""",
        (decision, reviewed_by, request_id)
    )
    if decision == 'Approved':
        # Find active allocation and move student
        alloc = db.fetchone(
            "SELECT * FROM Allocations WHERE student_id=? AND status='Active'",
            (req['student_id'],)
        )
        if alloc:
            vacate_room(alloc['allocation_id'])
        allocate_room(req['student_id'], req['requested_room_id'])
