-- ============================================================
-- Hostel Management System - SQL Server Database Schema
-- Database: HostelManagementDB
-- ============================================================

USE master;
GO

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'HostelManagementDB')
BEGIN
    CREATE DATABASE HostelManagementDB;
    PRINT 'Database HostelManagementDB created successfully.';
END
ELSE
BEGIN
    PRINT 'Database HostelManagementDB already exists.';
END
GO

USE HostelManagementDB;
GO

-- ============================================================
-- TABLE: Users
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
BEGIN
    CREATE TABLE Users (
        user_id       INT IDENTITY(1,1) PRIMARY KEY,
        full_name     NVARCHAR(150)  NOT NULL,
        email         NVARCHAR(200)  NOT NULL UNIQUE,
        password_hash NVARCHAR(256)  NOT NULL,
        phone         NVARCHAR(20)   NULL,
        role          NVARCHAR(20)   NOT NULL DEFAULT 'student'
                      CHECK (role IN ('student','admin')),
        account_status NVARCHAR(20)  NOT NULL DEFAULT 'active'
                      CHECK (account_status IN ('active','inactive','suspended')),
        created_at    DATETIME2      NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table Users created.';
END
GO

-- ============================================================
-- TABLE: Students
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Students' AND xtype='U')
BEGIN
    CREATE TABLE Students (
        student_id          INT IDENTITY(1,1) PRIMARY KEY,
        user_id             INT            NOT NULL UNIQUE
                            REFERENCES Users(user_id) ON DELETE CASCADE,
        registration_number NVARCHAR(50)   NOT NULL UNIQUE,
        department          NVARCHAR(100)  NULL,
        academic_year       NVARCHAR(20)   NULL,
        guardian_name       NVARCHAR(150)  NULL,
        guardian_phone      NVARCHAR(20)   NULL,
        address             NVARCHAR(500)  NULL
    );
    PRINT 'Table Students created.';
END
GO

-- ============================================================
-- TABLE: Rooms
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Rooms' AND xtype='U')
BEGIN
    CREATE TABLE Rooms (
        room_id        INT IDENTITY(1,1) PRIMARY KEY,
        room_number    NVARCHAR(20)   NOT NULL UNIQUE,
        floor          INT            NOT NULL DEFAULT 1,
        room_type      NVARCHAR(50)   NOT NULL DEFAULT 'Single'
                       CHECK (room_type IN ('Single','Double','Triple','Dormitory')),
        capacity       INT            NOT NULL DEFAULT 1
                       CHECK (capacity > 0),
        occupied_count INT            NOT NULL DEFAULT 0
                       CHECK (occupied_count >= 0),
        status         NVARCHAR(20)   NOT NULL DEFAULT 'Available'
                       CHECK (status IN ('Available','Full','Maintenance','Closed'))
    );
    PRINT 'Table Rooms created.';
END
GO

-- ============================================================
-- TABLE: RoomAllocations
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RoomAllocations' AND xtype='U')
BEGIN
    CREATE TABLE RoomAllocations (
        allocation_id   INT IDENTITY(1,1) PRIMARY KEY,
        student_id      INT         NOT NULL REFERENCES Students(student_id),
        room_id         INT         NOT NULL REFERENCES Rooms(room_id),
        allocation_date DATE        NOT NULL DEFAULT CAST(GETDATE() AS DATE),
        vacate_date     DATE        NULL,
        status          NVARCHAR(20) NOT NULL DEFAULT 'Active'
                        CHECK (status IN ('Active','Vacated','Transferred'))
    );
    PRINT 'Table RoomAllocations created.';
END
GO

-- ============================================================
-- TABLE: RoomChangeRequests
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RoomChangeRequests' AND xtype='U')
BEGIN
    CREATE TABLE RoomChangeRequests (
        request_id        INT IDENTITY(1,1) PRIMARY KEY,
        student_id        INT          NOT NULL REFERENCES Students(student_id),
        current_room_id   INT          NOT NULL REFERENCES Rooms(room_id),
        requested_room_id INT          NOT NULL REFERENCES Rooms(room_id),
        reason            NVARCHAR(MAX) NULL,
        status            NVARCHAR(20) NOT NULL DEFAULT 'Pending'
                          CHECK (status IN ('Pending','Approved','Rejected')),
        requested_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
        reviewed_at       DATETIME2    NULL
    );
    PRINT 'Table RoomChangeRequests created.';
END
GO

-- ============================================================
-- TABLE: LeaveRequests
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LeaveRequests' AND xtype='U')
BEGIN
    CREATE TABLE LeaveRequests (
        leave_id          INT IDENTITY(1,1) PRIMARY KEY,
        student_id        INT          NOT NULL REFERENCES Students(student_id),
        start_date        DATE         NOT NULL,
        end_date          DATE         NOT NULL,
        destination       NVARCHAR(200) NOT NULL,
        reason            NVARCHAR(MAX) NOT NULL,
        emergency_contact NVARCHAR(20)  NOT NULL,
        status            NVARCHAR(20)  NOT NULL DEFAULT 'Pending'
                          CHECK (status IN ('Pending','Approved','Rejected')),
        admin_remarks     NVARCHAR(MAX) NULL,
        created_at        DATETIME2     NOT NULL DEFAULT GETDATE(),
        reviewed_at       DATETIME2     NULL,
        CONSTRAINT CK_Leave_Dates CHECK (end_date >= start_date)
    );
    PRINT 'Table LeaveRequests created.';
END
GO

-- ============================================================
-- TABLE: Complaints
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Complaints' AND xtype='U')
BEGIN
    CREATE TABLE Complaints (
        complaint_id      INT IDENTITY(1,1) PRIMARY KEY,
        student_id        INT          NOT NULL REFERENCES Students(student_id),
        title             NVARCHAR(200) NOT NULL,
        category          NVARCHAR(50)  NOT NULL
                          CHECK (category IN ('Maintenance','Electricity','Water','Cleanliness','Food','Other')),
        description       NVARCHAR(MAX) NOT NULL,
        priority          NVARCHAR(20)  NOT NULL DEFAULT 'Medium'
                          CHECK (priority IN ('Low','Medium','High','Urgent')),
        status            NVARCHAR(20)  NOT NULL DEFAULT 'Submitted'
                          CHECK (status IN ('Submitted','In Progress','Resolved','Closed')),
        resolution_notes  NVARCHAR(MAX) NULL,
        created_at        DATETIME2     NOT NULL DEFAULT GETDATE(),
        updated_at        DATETIME2     NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Table Complaints created.';
END
GO

-- ============================================================
-- TABLE: Announcements
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Announcements' AND xtype='U')
BEGIN
    CREATE TABLE Announcements (
        announcement_id INT IDENTITY(1,1) PRIMARY KEY,
        title           NVARCHAR(200) NOT NULL,
        message         NVARCHAR(MAX) NOT NULL,
        category        NVARCHAR(50)  NOT NULL DEFAULT 'General'
                        CHECK (category IN ('General','Academic','Maintenance','Events','Emergency')),
        created_by      INT           NOT NULL REFERENCES Users(user_id),
        created_at      DATETIME2     NOT NULL DEFAULT GETDATE(),
        expiry_date     DATE          NULL
    );
    PRINT 'Table Announcements created.';
END
GO

-- ============================================================
-- INDEXES
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_Users_Email')
    CREATE INDEX IX_Users_Email ON Users(email);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_Students_RegNum')
    CREATE INDEX IX_Students_RegNum ON Students(registration_number);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_RoomAlloc_Student')
    CREATE INDEX IX_RoomAlloc_Student ON RoomAllocations(student_id, status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_Leave_Student')
    CREATE INDEX IX_Leave_Student ON LeaveRequests(student_id, status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_Complaint_Student')
    CREATE INDEX IX_Complaint_Student ON Complaints(student_id, status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_Announce_Expiry')
    CREATE INDEX IX_Announce_Expiry ON Announcements(expiry_date);
GO

-- ============================================================
-- SAMPLE DATA
-- ============================================================

-- Rooms (password not needed for rooms)
IF NOT EXISTS (SELECT 1 FROM Rooms)
BEGIN
    INSERT INTO Rooms (room_number, floor, room_type, capacity, occupied_count, status) VALUES
    ('101', 1, 'Single',    1, 0, 'Available'),
    ('102', 1, 'Double',    2, 0, 'Available'),
    ('103', 1, 'Double',    2, 0, 'Available'),
    ('104', 1, 'Triple',    3, 0, 'Available'),
    ('201', 2, 'Single',    1, 0, 'Available'),
    ('202', 2, 'Double',    2, 0, 'Available'),
    ('203', 2, 'Triple',    3, 0, 'Available'),
    ('204', 2, 'Dormitory', 6, 0, 'Available'),
    ('301', 3, 'Single',    1, 0, 'Available'),
    ('302', 3, 'Double',    2, 0, 'Available'),
    ('303', 3, 'Maintenance', 2, 0, 'Maintenance');
    PRINT 'Sample rooms inserted.';
END
GO

PRINT '=== HostelManagementDB schema setup complete ===';
GO
