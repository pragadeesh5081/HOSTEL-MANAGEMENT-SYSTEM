"""
Database layer — SQLite (no installation required, built into Python).
The database file is created automatically at first run.
"""
import sqlite3
import os
import shutil
import click
from flask import g, current_app


def get_db_path():
    """Return the active SQLite database path, supporting Vercel / serverless environments."""
    if os.environ.get('DATABASE_FILE'):
        return os.environ['DATABASE_FILE']

    # On Vercel / AWS Lambda, the deployment directory is read-only.
    # We use /tmp which is writable.
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        tmp_db = '/tmp/hms.db'
        if not os.path.exists(tmp_db):
            repo_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hms.db')
            if os.path.exists(repo_db):
                try:
                    shutil.copy2(repo_db, tmp_db)
                except Exception as e:
                    print(f"[HMS] Notice: could not copy repo db to /tmp: {e}")
        return tmp_db

    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hms.db')


DATABASE_FILE = get_db_path()


def get_db():
    """Return the per-request SQLite connection stored on Flask's g object."""
    if 'db' not in g:
        db_path = get_db_path()
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row   # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
        try:
            g.db.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            g.db.execute("PRAGMA journal_mode = DELETE")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Convenience helpers ──────────────────────────────────────

class DateString(str):
    """Subclass of str that provides .strftime() for SQLite datetime strings."""
    def strftime(self, fmt):
        try:
            from datetime import datetime
            clean = self.strip().replace('Z', '')
            if 'T' in clean:
                dt = datetime.fromisoformat(clean)
            elif ' ' in clean:
                dt = datetime.strptime(clean.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(clean, '%Y-%m-%d')
            return dt.strftime(fmt)
        except Exception:
            return self


DATE_KEYS = {
    'created_at', 'updated_at', 'requested_at', 'reviewed_at',
    'allocation_date', 'vacate_date', 'start_date', 'end_date',
    'joined_date', 'expiry_date'
}


def _wrap_row(d):
    for k, v in d.items():
        if isinstance(v, str) and (k in DATE_KEYS or k.endswith('_date') or k.endswith('_at')):
            d[k] = DateString(v)
    return d


def fetchall(sql, params=()):
    """Execute a SELECT and return a list of dict-like rows."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    return [_wrap_row(dict(r)) for r in rows]


def fetchone(sql, params=()):
    """Execute a SELECT and return the first row as a dict, or None."""
    cur = get_db().execute(sql, params)
    row = cur.fetchone()
    return _wrap_row(dict(row)) if row else None



def execute(sql, params=()):
    """Execute INSERT/UPDATE/DELETE.  Returns the last inserted row id."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def executemany(sql, params_list):
    """Execute the same statement for every item in params_list."""
    db = get_db()
    db.executemany(sql, params_list)
    db.commit()


# ── Schema initialisation ─────────────────────────────────────

def init_db():
    """Create all tables if they don't exist yet and ensure default admin account exists."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA_SQL)
    db.commit()

    # Seed default admin if no admin exists yet
    cur = db.execute("SELECT 1 FROM Users WHERE role = 'admin' LIMIT 1")
    if not cur.fetchone():
        try:
            from werkzeug.security import generate_password_hash
            default_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@hms.com')
            default_pass = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'Admin@1234')
            pw_hash = generate_password_hash(default_pass)
            db.execute(
                "INSERT INTO Users (email, password_hash, role, full_name, phone) VALUES (?, ?, 'admin', 'System Administrator', '1234567890')",
                (default_email.lower().strip(), pw_hash)
            )
            db.commit()
            print(f"[HMS] Seeded default administrator account: {default_email}")
        except Exception as e:
            print(f"[HMS] Note: unable to seed default admin: {e}")

    db.close()
    print(f"[HMS] Database initialised at: {db_path}")


SCHEMA_SQL = """
-- Users
CREATE TABLE IF NOT EXISTS Users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('admin','student')),
    full_name     TEXT NOT NULL,
    phone         TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Students
CREATE TABLE IF NOT EXISTS Students (
    student_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL UNIQUE REFERENCES Users(user_id) ON DELETE CASCADE,
    registration_number TEXT NOT NULL UNIQUE,
    department          TEXT,
    academic_year       TEXT,
    guardian_name       TEXT,
    guardian_phone      TEXT,
    address             TEXT,
    account_status      TEXT NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','inactive','suspended')),
    joined_date         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Rooms
CREATE TABLE IF NOT EXISTS Rooms (
    room_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number    TEXT NOT NULL UNIQUE,
    floor          INTEGER NOT NULL DEFAULT 1,
    room_type      TEXT NOT NULL DEFAULT 'Single' CHECK(room_type IN ('Single','Double','Triple','Dormitory')),
    capacity       INTEGER NOT NULL DEFAULT 1,
    occupied_count INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available','Full','Maintenance','Closed')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Allocations
CREATE TABLE IF NOT EXISTS Allocations (
    allocation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    room_id         INTEGER NOT NULL REFERENCES Rooms(room_id) ON DELETE CASCADE,
    allocation_date TEXT NOT NULL,
    vacate_date     TEXT,
    status          TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Vacated')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Room Change Requests
CREATE TABLE IF NOT EXISTS RoomChangeRequests (
    request_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    current_room_id   INTEGER NOT NULL REFERENCES Rooms(room_id),
    requested_room_id INTEGER NOT NULL REFERENCES Rooms(room_id),
    reason            TEXT,
    status            TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    reviewed_by       INTEGER REFERENCES Users(user_id),
    reviewed_at       TEXT,
    requested_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Leave Requests
CREATE TABLE IF NOT EXISTS LeaveRequests (
    leave_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    start_date        TEXT NOT NULL,
    end_date          TEXT NOT NULL,
    destination       TEXT,
    reason            TEXT,
    emergency_contact TEXT,
    status            TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    admin_remarks     TEXT,
    reviewed_by       INTEGER REFERENCES Users(user_id),
    reviewed_at       TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Complaints
CREATE TABLE IF NOT EXISTS Complaints (
    complaint_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    category         TEXT NOT NULL DEFAULT 'Other',
    description      TEXT,
    priority         TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High','Urgent')),
    status           TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted','In Progress','Resolved','Closed')),
    resolution_notes TEXT,
    resolved_by      INTEGER REFERENCES Users(user_id),
    resolved_at      TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Announcements
CREATE TABLE IF NOT EXISTS Announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'General',
    created_by      INTEGER NOT NULL REFERENCES Users(user_id),
    expiry_date     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sample rooms
INSERT OR IGNORE INTO Rooms (room_number, floor, room_type, capacity) VALUES
  ('101', 1, 'Single',    1),
  ('102', 1, 'Double',    2),
  ('103', 1, 'Double',    2),
  ('104', 1, 'Triple',    3),
  ('105', 1, 'Dormitory', 6),
  ('201', 2, 'Single',    1),
  ('202', 2, 'Double',    2),
  ('203', 2, 'Double',    2),
  ('204', 2, 'Triple',    3),
  ('205', 2, 'Triple',    3),
  ('301', 3, 'Single',    1),
  ('302', 3, 'Double',    2),
  ('303', 3, 'Dormitory', 8);
"""
