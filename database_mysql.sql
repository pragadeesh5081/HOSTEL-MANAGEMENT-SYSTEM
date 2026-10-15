-- ============================================================
-- Hostel Management System — MySQL 8.0 Schema
-- Run: mysql -u root -p < database_mysql.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS HostelManagementDB
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE HostelManagementDB;

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL,
    role          ENUM('admin','student') NOT NULL DEFAULT 'student',
    full_name     VARCHAR(200) NOT NULL,
    phone         VARCHAR(20),
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role  (role)
) ENGINE=InnoDB;

-- ── Students ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Students (
    student_id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT NOT NULL UNIQUE,
    registration_number VARCHAR(50) NOT NULL UNIQUE,
    department          VARCHAR(100),
    academic_year       VARCHAR(50),
    guardian_name       VARCHAR(200),
    guardian_phone      VARCHAR(20),
    address             TEXT,
    account_status      ENUM('active','inactive','suspended') NOT NULL DEFAULT 'active',
    joined_date         DATE,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    INDEX idx_students_user_id (user_id),
    INDEX idx_students_reg_no  (registration_number)
) ENGINE=InnoDB;

-- ── Rooms ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Rooms (
    room_id        INT AUTO_INCREMENT PRIMARY KEY,
    room_number    VARCHAR(20) NOT NULL UNIQUE,
    floor          INT NOT NULL DEFAULT 1,
    room_type      ENUM('Single','Double','Triple','Dormitory') NOT NULL DEFAULT 'Single',
    capacity       INT NOT NULL DEFAULT 1,
    occupied_count INT NOT NULL DEFAULT 0,
    status         ENUM('Available','Full','Maintenance','Closed') NOT NULL DEFAULT 'Available',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rooms_status (status),
    INDEX idx_rooms_floor  (floor),
    CONSTRAINT chk_capacity CHECK (capacity >= 1),
    CONSTRAINT chk_occupied CHECK (occupied_count >= 0)
) ENGINE=InnoDB;

-- ── Allocations ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Allocations (
    allocation_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT NOT NULL,
    room_id         INT NOT NULL,
    allocation_date DATE NOT NULL,
    vacate_date     DATE,
    status          ENUM('Active','Vacated') NOT NULL DEFAULT 'Active',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id)    REFERENCES Rooms(room_id) ON DELETE CASCADE,
    INDEX idx_alloc_student (student_id),
    INDEX idx_alloc_room    (room_id),
    INDEX idx_alloc_status  (status)
) ENGINE=InnoDB;

-- ── Room Change Requests ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS RoomChangeRequests (
    request_id        INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT NOT NULL,
    current_room_id   INT NOT NULL,
    requested_room_id INT NOT NULL,
    reason            TEXT,
    status            ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
    reviewed_by       INT,
    reviewed_at       DATETIME,
    requested_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id)        REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (current_room_id)   REFERENCES Rooms(room_id),
    FOREIGN KEY (requested_room_id) REFERENCES Rooms(room_id),
    FOREIGN KEY (reviewed_by)       REFERENCES Users(user_id),
    INDEX idx_rcr_student (student_id),
    INDEX idx_rcr_status  (status)
) ENGINE=InnoDB;

-- ── Leave Requests ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS LeaveRequests (
    leave_id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT NOT NULL,
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    destination       VARCHAR(500),
    reason            TEXT,
    emergency_contact VARCHAR(20),
    status            ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
    admin_remarks     TEXT,
    reviewed_by       INT,
    reviewed_at       DATETIME,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id)  REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES Users(user_id),
    INDEX idx_leave_student (student_id),
    INDEX idx_leave_status  (status)
) ENGINE=InnoDB;

-- ── Complaints ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Complaints (
    complaint_id     INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    title            VARCHAR(200) NOT NULL,
    category         ENUM('Maintenance','Electricity','Water','Cleanliness','Food','Other') NOT NULL DEFAULT 'Other',
    description      TEXT,
    priority         ENUM('Low','Medium','High','Urgent') NOT NULL DEFAULT 'Medium',
    status           ENUM('Submitted','In Progress','Resolved','Closed') NOT NULL DEFAULT 'Submitted',
    resolution_notes TEXT,
    resolved_by      INT,
    resolved_at      DATETIME,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id)  REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES Users(user_id),
    INDEX idx_complaints_student  (student_id),
    INDEX idx_complaints_status   (status),
    INDEX idx_complaints_priority (priority)
) ENGINE=InnoDB;

-- ── Announcements ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Announcements (
    announcement_id INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    message         TEXT NOT NULL,
    category        ENUM('General','Academic','Maintenance','Events','Emergency') NOT NULL DEFAULT 'General',
    created_by      INT NOT NULL,
    expiry_date     DATE,
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES Users(user_id),
    INDEX idx_ann_active  (is_active),
    INDEX idx_ann_expiry  (expiry_date)
) ENGINE=InnoDB;

-- ── Sample Room Data ──────────────────────────────────────────
INSERT IGNORE INTO Rooms (room_number, floor, room_type, capacity, status) VALUES
('101', 1, 'Single',    1, 'Available'),
('102', 1, 'Double',    2, 'Available'),
('103', 1, 'Double',    2, 'Available'),
('104', 1, 'Triple',    3, 'Available'),
('105', 1, 'Dormitory', 6, 'Available'),
('201', 2, 'Single',    1, 'Available'),
('202', 2, 'Double',    2, 'Available'),
('203', 2, 'Double',    2, 'Available'),
('204', 2, 'Triple',    3, 'Available'),
('205', 2, 'Triple',    3, 'Available'),
('301', 3, 'Single',    1, 'Available'),
('302', 3, 'Double',    2, 'Available'),
('303', 3, 'Dormitory', 8, 'Available');

SELECT 'HostelManagementDB created successfully!' AS Status;
SELECT CONCAT(COUNT(*), ' rooms ready') AS Rooms FROM Rooms;
