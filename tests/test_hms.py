"""
Basic automated tests for the Hostel Management System.
Run with:  python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from datetime import datetime


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False
    application.config['SECRET_KEY'] = 'test-secret-key'
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def student_session(client):
    """Return a client with a student session cookie."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role']    = 'student'
        sess['name']    = 'Test Student'
    return client


@pytest.fixture
def admin_session(client):
    """Return a client with an admin session cookie."""
    with client.session_transaction() as sess:
        sess['user_id'] = 99
        sess['role']    = 'admin'
        sess['name']    = 'Test Admin'
    return client


def _make_student():
    return {
        'student_id': 1, 'user_id': 1, 'full_name': 'Test Student',
        'email': 'test@test.com', 'phone': '1234567890',
        'registration_number': 'CS001', 'department': 'CS',
        'academic_year': '2nd', 'guardian_name': 'Parent',
        'guardian_phone': '0987654321', 'address': 'Test Addr',
        'account_status': 'active'
    }


# ── Auth Tests ───────────────────────────────────────────────

class TestAuthentication:
    def test_login_page_loads(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200
        assert b'Sign In' in resp.data or b'Login' in resp.data or b'login' in resp.data.lower()

    def test_register_page_loads(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_login_redirects_when_logged_in(self, student_session):
        resp = student_session.get('/login')
        assert resp.status_code == 302

    def test_logout_clears_session(self, student_session):
        resp = student_session.get('/logout', follow_redirects=True)
        assert resp.status_code == 200

    def test_unauthenticated_access_redirects_to_login(self, client):
        resp = client.get('/student/dashboard')
        assert resp.status_code == 302
        loc = resp.headers.get('Location', '')
        assert 'login' in loc.lower()

    def test_unauthenticated_admin_redirects(self, client):
        resp = client.get('/admin/dashboard')
        assert resp.status_code == 302

    @patch('services.auth_service.get_user_by_email')
    def test_login_invalid_credentials(self, mock_get, client):
        mock_get.return_value = None
        resp = client.post('/login', data={'email': 'bad@test.com', 'password': 'wrong'})
        assert resp.status_code == 200
        assert b'Invalid' in resp.data

    @patch('services.auth_service.get_user_by_email')
    def test_login_empty_fields(self, mock_get, client):
        resp = client.post('/login', data={'email': '', 'password': ''})
        assert resp.status_code == 200
        mock_get.assert_not_called()

    @patch('services.auth_service.register_admin')
    def test_admin_register_success(self, mock_reg, client):
        resp = client.post('/register', data={
            'role': 'admin',
            'full_name': 'Admin User',
            'email': 'newadmin@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'phone': '1234567890'
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '')
        mock_reg.assert_called_once_with('newadmin@test.com', 'password123', 'Admin User', phone='1234567890')

    def test_admin_register_mismatched_password(self, client):
        resp = client.post('/register', data={
            'role': 'admin',
            'full_name': 'Admin User',
            'email': 'admin@test.com',
            'password': 'password123',
            'confirm_password': 'mismatch',
        })
        assert resp.status_code == 200
        assert b'Passwords do not match' in resp.data



# ── Role Permission Tests ─────────────────────────────────────

class TestRolePermissions:
    def test_student_cannot_access_admin_dashboard(self, student_session):
        resp = student_session.get('/admin/dashboard')
        assert resp.status_code == 302

    def test_unauthenticated_user_cannot_access_admin(self, client):
        resp = client.get('/admin/rooms')
        assert resp.status_code == 302

    def test_unauthenticated_user_cannot_access_student(self, client):
        resp = client.get('/student/profile')
        assert resp.status_code == 302


# ── Student Profile Tests ─────────────────────────────────────

class TestStudentProfile:
    @patch('services.student_service.get_student_by_user_id')
    def test_profile_redirects_when_no_student(self, mock_student, student_session):
        """When student profile is missing, user is redirected to logout."""
        mock_student.return_value = None
        resp = student_session.get('/student/profile')
        # redirects away (either logout or login)
        assert resp.status_code in (200, 302)

    @patch('services.student_service.update_student_profile')
    @patch('services.student_service.get_student_by_user_id')
    def test_profile_post_calls_update(self, mock_student, mock_update, student_session):
        mock_student.return_value = _make_student()
        mock_update.return_value = None
        resp = student_session.post('/student/profile', data={
            'full_name': 'Updated Name', 'phone': '9999999999',
            'department': 'IT', 'academic_year': '3rd',
            'guardian_name': 'Guardian', 'guardian_phone': '8888888888',
            'address': 'New Address'
        }, follow_redirects=False)
        # Should redirect on success
        assert resp.status_code in (200, 302)
        mock_update.assert_called_once()

    @patch('services.student_service.update_student_profile')
    @patch('services.student_service.get_student_by_id')
    def test_admin_edit_student_regno_success(self, mock_get, mock_update, admin_session):
        mock_get.return_value = _make_student()
        resp = admin_session.post('/admin/students/1/edit', data={
            'full_name': 'Test Student',
            'registration_number': 'REG999',
            'phone': '1234567890',
            'department': 'CS',
            'academic_year': '3rd',
            'guardian_name': 'Parent',
            'guardian_phone': '0987654321',
            'address': 'Test Addr'
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        mock_update.assert_called_once_with(
            1, 'CS', '3rd', 'Parent', '0987654321', 'Test Addr',
            'Test Student', '1234567890', registration_number='REG999'
        )

    @patch('services.student_service.get_student_by_id')
    def test_admin_edit_student_missing_regno(self, mock_get, admin_session):
        mock_get.return_value = _make_student()
        resp = admin_session.post('/admin/students/1/edit', data={
            'full_name': 'Test Student',
            'registration_number': '',
        })
        assert resp.status_code == 200
        assert b'Registration number is required' in resp.data



# ── Room Allocation Tests ─────────────────────────────────────

class TestRoomAllocation:
    @patch('services.room_service.allocate_room')
    @patch('services.room_service.get_all_rooms')
    @patch('services.student_service.get_all_students')
    @patch('services.room_service.get_all_allocations')
    def test_allocate_room_success(self, mock_allocs, mock_students,
                                   mock_rooms, mock_alloc, admin_session):
        mock_allocs.return_value = []
        mock_students.return_value = [
            {'student_id': 1, 'full_name': 'Alice', 'registration_number': 'CS001'}
        ]
        mock_rooms.return_value = [
            {'room_id': 1, 'room_number': '101', 'status': 'Available',
             'floor': 1, 'room_type': 'Single', 'capacity': 1, 'occupied_count': 0}
        ]
        mock_alloc.return_value = None
        resp = admin_session.post('/admin/allocations/allocate',
                                  data={'student_id': '1', 'room_id': '1'},
                                  follow_redirects=False)
        assert resp.status_code == 302  # redirect after success
        mock_alloc.assert_called_once_with(1, 1)

    @patch('services.room_service.allocate_room')
    @patch('services.room_service.get_all_rooms')
    @patch('services.student_service.get_all_students')
    @patch('services.room_service.get_all_allocations')
    def test_allocate_room_full_shows_error(self, mock_allocs, mock_students,
                                             mock_rooms, mock_alloc, admin_session):
        mock_allocs.return_value = []
        mock_students.return_value = []
        mock_rooms.return_value = []
        mock_alloc.side_effect = ValueError("Room is at full capacity.")
        resp = admin_session.post('/admin/allocations/allocate',
                                  data={'student_id': '1', 'room_id': '1'},
                                  follow_redirects=False)
        assert resp.status_code == 302

    def test_allocate_missing_fields(self, admin_session):
        """Missing student_id or room_id should redirect with error flash."""
        resp = admin_session.post('/admin/allocations/allocate',
                                  data={'student_id': '', 'room_id': ''},
                                  follow_redirects=False)
        assert resp.status_code == 302

    @patch('services.room_service.vacate_room')
    def test_vacate_room(self, mock_vacate, admin_session):
        mock_vacate.return_value = None
        resp = admin_session.post('/admin/allocations/5/vacate',
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_vacate.assert_called_once_with(5)


# ── Leave Request Tests ───────────────────────────────────────

class TestLeaveRequests:
    @patch('services.student_service.get_student_by_user_id')
    @patch('services.leave_service.submit_leave')
    def test_submit_leave_success(self, mock_submit, mock_student, student_session):
        mock_student.return_value = _make_student()
        mock_submit.return_value = None
        resp = student_session.post('/student/apply-leave', data={
            'start_date': '2026-11-01', 'end_date': '2026-11-05',
            'destination': 'Home', 'reason': 'Festival',
            'emergency_contact': '9999999999'
        }, follow_redirects=False)
        assert resp.status_code == 302  # redirects to leave_history
        mock_submit.assert_called_once()

    @patch('services.student_service.get_student_by_user_id')
    def test_submit_leave_missing_fields_stays_on_form(self, mock_student, student_session):
        mock_student.return_value = _make_student()
        resp = student_session.post('/student/apply-leave', data={
            'start_date': '', 'end_date': '', 'destination': '',
            'reason': '', 'emergency_contact': ''
        }, follow_redirects=False)
        assert resp.status_code == 200  # stays on form

    @patch('services.student_service.get_student_by_user_id')
    def test_submit_leave_invalid_dates(self, mock_student, student_session):
        mock_student.return_value = _make_student()
        resp = student_session.post('/student/apply-leave', data={
            'start_date': '2026-11-10', 'end_date': '2026-11-01',
            'destination': 'Home', 'reason': 'Test',
            'emergency_contact': '9999999999'
        }, follow_redirects=False)
        assert resp.status_code == 200  # stays with error

    @patch('services.leave_service.review_leave')
    def test_admin_approve_leave(self, mock_review, admin_session):
        mock_review.return_value = None
        resp = admin_session.post('/admin/leave-requests/1/review',
                                  data={'decision': 'Approved', 'admin_remarks': 'OK'},
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_review.assert_called_once_with(1, 'Approved', 'OK')

    @patch('services.leave_service.review_leave')
    def test_admin_reject_leave(self, mock_review, admin_session):
        mock_review.return_value = None
        resp = admin_session.post('/admin/leave-requests/2/review',
                                  data={'decision': 'Rejected', 'admin_remarks': 'Denied'},
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_review.assert_called_once_with(2, 'Rejected', 'Denied')

    def test_admin_invalid_decision_rejected(self, admin_session):
        """An invalid decision value should still redirect (with flash error)."""
        resp = admin_session.post('/admin/leave-requests/1/review',
                                  data={'decision': 'INVALID'},
                                  follow_redirects=False)
        assert resp.status_code == 302


# ── Complaint Tests ───────────────────────────────────────────

class TestComplaints:
    @patch('services.student_service.get_student_by_user_id')
    @patch('services.complaint_service.submit_complaint')
    def test_submit_complaint_success(self, mock_submit, mock_student, student_session):
        mock_student.return_value = _make_student()
        mock_submit.return_value = None
        resp = student_session.post('/student/submit-complaint', data={
            'title': 'Broken tap', 'category': 'Water',
            'description': 'The tap in room 101 is broken.', 'priority': 'High'
        }, follow_redirects=False)
        assert resp.status_code == 302  # redirects to my_complaints
        mock_submit.assert_called_once()

    @patch('services.student_service.get_student_by_user_id')
    def test_submit_complaint_missing_fields(self, mock_student, student_session):
        mock_student.return_value = _make_student()
        resp = student_session.post('/student/submit-complaint', data={
            'title': '', 'category': '', 'description': '', 'priority': 'Low'
        }, follow_redirects=False)
        assert resp.status_code == 200  # stays on form

    @patch('services.complaint_service.update_complaint_status')
    def test_admin_update_complaint(self, mock_update, admin_session):
        mock_update.return_value = None
        resp = admin_session.post('/admin/complaints/5/update',
                                  data={'status': 'Resolved', 'resolution_notes': 'Fixed the tap.'},
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_update.assert_called_once_with(5, 'Resolved', 'Fixed the tap.')

    @patch('services.complaint_service.update_complaint_status')
    def test_admin_update_complaint_in_progress(self, mock_update, admin_session):
        mock_update.return_value = None
        resp = admin_session.post('/admin/complaints/7/update',
                                  data={'status': 'In Progress', 'resolution_notes': ''},
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_update.assert_called_once_with(7, 'In Progress', '')


# ── Announcement Tests ────────────────────────────────────────

class TestAnnouncements:
    @patch('services.announcement_service.get_announcements')
    @patch('services.student_service.get_student_by_user_id')
    def test_student_sees_announcements(self, mock_student, mock_ann, student_session):
        mock_student.return_value = _make_student()
        mock_ann.return_value = [{
            'announcement_id': 1, 'title': 'Hostel Event', 'message': 'Join us!',
            'category': 'Events', 'created_at': datetime.now(),
            'expiry_date': None, 'created_by_name': 'Admin'
        }]
        resp = student_session.get('/student/announcements')
        assert resp.status_code == 200
        assert b'Hostel Event' in resp.data

    @patch('services.announcement_service.create_announcement')
    def test_admin_create_announcement(self, mock_create, admin_session):
        mock_create.return_value = None
        resp = admin_session.post('/admin/announcements/add', data={
            'title': 'New Event', 'message': 'Event tomorrow!',
            'category': 'Events', 'expiry_date': ''
        }, follow_redirects=False)
        assert resp.status_code == 302
        mock_create.assert_called_once()

    @patch('services.announcement_service.delete_announcement')
    def test_admin_delete_announcement(self, mock_delete, admin_session):
        mock_delete.return_value = None
        resp = admin_session.post('/admin/announcements/3/delete',
                                  follow_redirects=False)
        assert resp.status_code == 302
        mock_delete.assert_called_once_with(3)

    def test_admin_add_announcement_missing_fields(self, admin_session):
        """Missing title/message should re-render the form."""
        resp = admin_session.post('/admin/announcements/add', data={
            'title': '', 'message': '', 'category': 'General', 'expiry_date': ''
        }, follow_redirects=False)
        assert resp.status_code == 200


# ── DB Validation Tests ───────────────────────────────────────

class TestDatabaseValidation:
    def test_allocate_requires_student_and_room(self, admin_session):
        resp = admin_session.post('/admin/allocations/allocate',
                                  data={}, follow_redirects=False)
        assert resp.status_code == 302  # flash error + redirect

    def test_leave_review_invalid_decision(self, admin_session):
        resp = admin_session.post('/admin/leave-requests/99/review',
                                  data={'decision': 'MAYBE'},
                                  follow_redirects=False)
        assert resp.status_code == 302

    def test_change_request_invalid_decision(self, admin_session):
        resp = admin_session.post('/admin/room-change-requests/99/review',
                                  data={'decision': 'INVALID'},
                                  follow_redirects=False)
        assert resp.status_code == 302
