"""
Database layer — Supports both SQLite (local development / testing) and
PostgreSQL / Neon (cloud / production on Vercel).
"""
import os
import re
import shutil
import sqlite3
from flask import g, current_app

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def get_postgres_url():
    """Return the active PostgreSQL connection URL if configured."""
    url = (
        os.environ.get('POSTGRES_URL') or
        os.environ.get('DATABASE_URL') or
        os.environ.get('POSTGRES_URL_NON_POOLING') or
        os.environ.get('POSTGRES_PRISMA_URL')
    )
    if not url:
        return None
    url = url.strip()
    # Normalize postgres:// to postgresql:// for compatibility
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


def is_postgres():
    """Check if the app is configured to use PostgreSQL / Neon."""
    return bool(get_postgres_url())


def connect_postgres():
    """Create and return a new PostgreSQL connection with SSL enabled."""
    if not PSYCOPG2_AVAILABLE:
        raise ImportError(
            "psycopg2-binary is required for PostgreSQL / Neon connections. "
            "Install with: pip install psycopg2-binary"
        )
    url = get_postgres_url()
    # Neon cloud requires sslmode=require
    if 'sslmode' not in url and 'localhost' not in url and '127.0.0.1' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}sslmode=require"
    return psycopg2.connect(url)


def get_db_path():
    """Return the active SQLite database path, supporting Vercel / serverless environments."""
    if os.environ.get('DATABASE_FILE'):
        return os.environ['DATABASE_FILE']

    # On Vercel / AWS Lambda without Postgres, the deployment directory is read-only.
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
    """Return the per-request database connection stored on Flask's g object."""
    if 'db' not in g:
        if is_postgres():
            g.db = connect_postgres()
        else:
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
    """Close the current request's database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Query Adapter ─────────────────────────────────────────────

def _adapt_query(sql):
    """Convert SQLite syntax (? placeholders, date functions) to PostgreSQL."""
    sql = re.sub(r"datetime\('now'\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"date\('now'\)", "CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = sql.replace('?', '%s')
    return sql


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
    if is_postgres():
        adapted_sql = _adapt_query(sql)
        conn = get_db()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(adapted_sql, params)
                rows = cur.fetchall()
                return [_wrap_row(dict(r)) for r in rows]
        except Exception:
            conn.rollback()
            raise
    else:
        cur = get_db().execute(sql, params)
        rows = cur.fetchall()
        return [_wrap_row(dict(r)) for r in rows]


def fetchone(sql, params=()):
    """Execute a SELECT and return the first row as a dict, or None."""
    if is_postgres():
        adapted_sql = _adapt_query(sql)
        conn = get_db()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(adapted_sql, params)
                row = cur.fetchone()
                return _wrap_row(dict(row)) if row else None
        except Exception:
            conn.rollback()
            raise
    else:
        cur = get_db().execute(sql, params)
        row = cur.fetchone()
        return _wrap_row(dict(row)) if row else None


def execute(sql, params=()):
    """Execute INSERT/UPDATE/DELETE. Returns the last inserted row id or affected count."""
    if is_postgres():
        adapted_sql = _adapt_query(sql)
        conn = get_db()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                is_insert = adapted_sql.strip().upper().startswith("INSERT")
                if is_insert and "RETURNING" not in adapted_sql.upper():
                    adapted_sql = adapted_sql.rstrip().rstrip(';') + " RETURNING *"
                    cur.execute(adapted_sql, params)
                    res = cur.fetchone()
                    conn.commit()
                    if res:
                        return list(res.values())[0]
                    return None
                else:
                    cur.execute(adapted_sql, params)
                    conn.commit()
                    return cur.rowcount
        except Exception:
            conn.rollback()
            raise
    else:
        db = get_db()
        cur = db.execute(sql, params)
        db.commit()
        return cur.lastrowid


def executemany(sql, params_list):
    """Execute the same statement for every item in params_list."""
    if is_postgres():
        adapted_sql = _adapt_query(sql)
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.executemany(adapted_sql, params_list)
                conn.commit()
        except Exception:
            conn.rollback()
            raise
    else:
        db = get_db()
        db.executemany(sql, params_list)
        db.commit()


# ── Schema initialisation ─────────────────────────────────────

def init_db():
    """Create all tables if they don't exist yet and ensure default admin account exists."""
    if is_postgres():
        conn = connect_postgres()
        try:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_POSTGRES_SQL)
                conn.commit()

                # Seed default admin if no admin exists yet
                cur.execute("SELECT 1 FROM Users WHERE role = 'admin' LIMIT 1")
                if not cur.fetchone():
                    try:
                        from werkzeug.security import generate_password_hash
                        default_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@hms.com')
                        default_pass = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'Admin@1234')
                        pw_hash = generate_password_hash(default_pass)
                        cur.execute(
                            "INSERT INTO Users (email, password_hash, role, full_name, phone) VALUES (%s, %s, 'admin', 'System Administrator', '1234567890')",
                            (default_email.lower().strip(), pw_hash)
                        )
                        conn.commit()
                        print(f"[HMS] Seeded default administrator account: {default_email}")
                    except Exception as e:
                        print(f"[HMS] Note: unable to seed default admin: {e}")
            print("[HMS] PostgreSQL / Neon database initialised successfully.")
        finally:
            conn.close()
    else:
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
        print(f"[HMS] SQLite database initialised at: {db_path}")


SCHEMA_POSTGRES_SQL = """
-- Users
CREATE TABLE IF NOT EXISTS Users (
    user_id       SERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'student' CHECK(role IN ('admin','student')),
    full_name     VARCHAR(255) NOT NULL,
    phone         VARCHAR(50),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Students
CREATE TABLE IF NOT EXISTS Students (
    student_id          SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL UNIQUE REFERENCES Users(user_id) ON DELETE CASCADE,
    registration_number VARCHAR(100) NOT NULL UNIQUE,
    department          VARCHAR(100),
    academic_year       VARCHAR(50),
    guardian_name       VARCHAR(150),
    guardian_phone      VARCHAR(50),
    address             TEXT,
    account_status      VARCHAR(20) NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','inactive','suspended')),
    joined_date         DATE DEFAULT CURRENT_DATE,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Rooms
CREATE TABLE IF NOT EXISTS Rooms (
    room_id        SERIAL PRIMARY KEY,
    room_number    VARCHAR(50) NOT NULL UNIQUE,
    floor          INTEGER NOT NULL DEFAULT 1,
    room_type      VARCHAR(50) NOT NULL DEFAULT 'Single' CHECK(room_type IN ('Single','Double','Triple','Dormitory')),
    capacity       INTEGER NOT NULL DEFAULT 1,
    occupied_count INTEGER NOT NULL DEFAULT 0,
    status         VARCHAR(50) NOT NULL DEFAULT 'Available' CHECK(status IN ('Available','Full','Maintenance','Closed')),
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Allocations
CREATE TABLE IF NOT EXISTS Allocations (
    allocation_id   SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    room_id         INTEGER NOT NULL REFERENCES Rooms(room_id) ON DELETE CASCADE,
    allocation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    vacate_date     DATE,
    status          VARCHAR(50) NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Vacated')),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Room Change Requests
CREATE TABLE IF NOT EXISTS RoomChangeRequests (
    request_id        SERIAL PRIMARY KEY,
    student_id        INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    current_room_id   INTEGER NOT NULL REFERENCES Rooms(room_id),
    requested_room_id INTEGER NOT NULL REFERENCES Rooms(room_id),
    reason            TEXT,
    status            VARCHAR(50) NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    reviewed_by       INTEGER REFERENCES Users(user_id),
    reviewed_at       TIMESTAMP,
    requested_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Leave Requests
CREATE TABLE IF NOT EXISTS LeaveRequests (
    leave_id          SERIAL PRIMARY KEY,
    student_id        INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    start_date        TEXT NOT NULL,
    end_date          TEXT NOT NULL,
    destination       TEXT,
    reason            TEXT,
    emergency_contact VARCHAR(50),
    status            VARCHAR(50) NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
    admin_remarks     TEXT,
    reviewed_by       INTEGER REFERENCES Users(user_id),
    reviewed_at       TIMESTAMP,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Complaints
CREATE TABLE IF NOT EXISTS Complaints (
    complaint_id     SERIAL PRIMARY KEY,
    student_id       INTEGER NOT NULL REFERENCES Students(student_id) ON DELETE CASCADE,
    title            VARCHAR(255) NOT NULL,
    category         VARCHAR(100) NOT NULL DEFAULT 'Other',
    description      TEXT,
    priority         VARCHAR(50) NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low','Medium','High','Urgent')),
    status           VARCHAR(50) NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted','In Progress','Resolved','Closed')),
    resolution_notes TEXT,
    resolved_by      INTEGER REFERENCES Users(user_id),
    resolved_at      TIMESTAMP,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Announcements
CREATE TABLE IF NOT EXISTS Announcements (
    announcement_id SERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    category        VARCHAR(100) NOT NULL DEFAULT 'General',
    created_by      INTEGER NOT NULL REFERENCES Users(user_id),
    expiry_date     DATE,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sample rooms
INSERT INTO Rooms (room_number, floor, room_type, capacity) VALUES
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
  ('303', 3, 'Dormitory', 8)
ON CONFLICT (room_number) DO NOTHING;
"""


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
