from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.decorators import admin_required
from services import (student_service, room_service, leave_service,
                      complaint_service, announcement_service, auth_service)
from models import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _get_stats():
    """Shared dashboard / reports stats dict."""
    total_students = len(student_service.get_all_students())
    room_stats     = room_service.get_room_stats()
    pending_leaves = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM LeaveRequests WHERE status='Pending'"
    )['cnt']
    open_complaints = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM Complaints WHERE status IN ('Submitted','In Progress')"
    )['cnt']
    pending_changes = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM RoomChangeRequests WHERE status='Pending'"
    )['cnt']
    return {
        'total_students' : total_students,
        'room_stats'     : room_stats,
        'pending_leaves' : pending_leaves,
        'open_complaints': open_complaints,
        'pending_changes': pending_changes,
    }


# ── Dashboard ─────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    stats           = _get_stats()
    complaint_chart = complaint_service.get_complaint_chart()
    recent_leaves   = leave_service.get_recent_leaves(5)
    recent_changes  = room_service.get_change_requests()[:5]
    return render_template('admin/dashboard.html',
        stats=stats, complaint_chart=complaint_chart,
        recent_leaves=recent_leaves,
        recent_changes=recent_changes)



# ── Students ──────────────────────────────────────────────────

@admin_bp.route('/students')
@admin_required
def students():
    all_students = student_service.get_all_students()
    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        full_name  = request.form.get('full_name','').strip()
        email      = request.form.get('email','').strip()
        phone      = request.form.get('phone','').strip() or None
        password   = request.form.get('password','')
        reg_num    = request.form.get('registration_number','').strip()
        department = request.form.get('department','').strip() or None
        acad_year  = request.form.get('academic_year','').strip() or None
        guardian   = request.form.get('guardian_name','').strip() or None
        gphone     = request.form.get('guardian_phone','').strip() or None
        address    = request.form.get('address','').strip() or None
        if not all([full_name, email, password, reg_num]):
            flash('Full name, email, password, and registration number are required.', 'danger')
        else:
            try:
                student_service.create_student_by_admin(
                    email, password, full_name, reg_num,
                    phone=phone, department=department, academic_year=acad_year,
                    guardian_name=guardian, guardian_phone=gphone, address=address
                )
                flash(f'Student {full_name} added successfully.', 'success')
                return redirect(url_for('admin.students'))
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                flash(f'Error creating student: {e}', 'danger')
    return render_template('admin/add_student.html')


@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    student = student_service.get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin.students'))
    if request.method == 'POST':
        full_name = request.form.get('full_name','').strip()
        reg_num   = request.form.get('registration_number','').strip()
        if not full_name:
            flash('Full name is required.', 'danger')
            return render_template('admin/edit_student.html', student=student)
        if not reg_num:
            flash('Registration number is required.', 'danger')
            return render_template('admin/edit_student.html', student=student)
        try:
            student_service.update_student_profile(
                student_id,
                request.form.get('department','').strip(),
                request.form.get('academic_year','').strip(),
                request.form.get('guardian_name','').strip(),
                request.form.get('guardian_phone','').strip(),
                request.form.get('address','').strip(),
                full_name,
                request.form.get('phone','').strip(),
                registration_number=reg_num
            )
            flash(f'Student {full_name} updated successfully.', 'success')
            return redirect(url_for('admin.students'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('admin/edit_student.html', student=student)



@admin_bp.route('/students/<int:student_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_student_status(student_id):
    try:
        student_service.toggle_student_status(student_id)
        flash('Account status updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.students'))


# ── Rooms ──────────────────────────────────────────────────────

@admin_bp.route('/rooms')
@admin_required
def rooms():
    all_rooms = room_service.get_all_rooms()
    return render_template('admin/rooms.html', rooms=all_rooms)


@admin_bp.route('/rooms/add', methods=['GET', 'POST'])
@admin_required
def add_room():
    if request.method == 'POST':
        room_number = request.form.get('room_number','').strip()
        floor       = request.form.get('floor', 1)
        room_type   = request.form.get('room_type','Single')
        capacity    = request.form.get('capacity', 1)
        if not room_number:
            flash('Room number is required.', 'danger')
        else:
            try:
                room_service.add_room(room_number, int(floor), room_type, int(capacity))
                flash(f'Room {room_number} added.', 'success')
                return redirect(url_for('admin.rooms'))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    return render_template('admin/add_room.html')


@admin_bp.route('/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_room(room_id):
    room = db.fetchone("SELECT * FROM Rooms WHERE room_id=?", (room_id,))
    if not room:
        flash('Room not found.', 'danger')
        return redirect(url_for('admin.rooms'))
    if request.method == 'POST':
        try:
            room_service.update_room(
                room_id,
                request.form.get('room_number','').strip(),
                int(request.form.get('floor', 1)),
                request.form.get('room_type','Single'),
                int(request.form.get('capacity', 1)),
                request.form.get('status','Available')
            )
            flash('Room updated.', 'success')
            return redirect(url_for('admin.rooms'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('admin/edit_room.html', room=room)


# ── Allocations ────────────────────────────────────────────────

@admin_bp.route('/allocations')
@admin_required
def allocations():
    all_allocs   = room_service.get_all_allocations()
    all_students = student_service.get_all_students()
    all_rooms    = room_service.get_all_rooms()
    return render_template('admin/allocations.html',
        allocations=all_allocs, students=all_students, rooms=all_rooms)


@admin_bp.route('/allocations/allocate', methods=['POST'])
@admin_required
def allocate_room():
    student_id = request.form.get('student_id')
    room_id    = request.form.get('room_id')
    if not student_id or not room_id:
        flash('Student and room are required.', 'danger')
    else:
        try:
            room_service.allocate_room(int(student_id), int(room_id))
            flash('Room allocated successfully.', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.allocations'))


@admin_bp.route('/allocations/<int:allocation_id>/vacate', methods=['POST'])
@admin_required
def vacate_room(allocation_id):
    try:
        room_service.vacate_room(allocation_id)
        flash('Room vacated successfully.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.allocations'))


# ── Room Change Requests ───────────────────────────────────────

@admin_bp.route('/room-change-requests')
@admin_required
def room_change_requests():
    reqs = room_service.get_change_requests()
    return render_template('admin/room_change_requests.html', requests=reqs)


@admin_bp.route('/room-change-requests/<int:request_id>/review', methods=['POST'])
@admin_required
def review_change_request(request_id):
    decision = request.form.get('decision')
    if decision not in ('Approved', 'Rejected'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('admin.room_change_requests'))
    try:
        room_service.review_change_request(request_id, decision, session['user_id'])
        flash(f'Request {decision.lower()}.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.room_change_requests'))


# ── Leave Requests ─────────────────────────────────────────────

@admin_bp.route('/leave-requests')
@admin_required
def leave_requests():
    leaves = leave_service.get_leaves()
    return render_template('admin/leave_requests.html', leaves=leaves)


@admin_bp.route('/leave-requests/<int:leave_id>/review', methods=['POST'])
@admin_required
def review_leave(leave_id):
    decision = request.form.get('decision')
    remarks  = request.form.get('admin_remarks', '')
    if decision not in ('Approved', 'Rejected'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('admin.leave_requests'))
    try:
        leave_service.review_leave(leave_id, decision, remarks)
        flash(f'Leave request {decision.lower()}.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.leave_requests'))


# ── Complaints ─────────────────────────────────────────────────

@admin_bp.route('/complaints')
@admin_required
def complaints():
    all_complaints = complaint_service.get_complaints()
    return render_template('admin/complaints.html', complaints=all_complaints)


@admin_bp.route('/complaints/<int:complaint_id>/update', methods=['POST'])
@admin_required
def update_complaint(complaint_id):
    status = request.form.get('status','')
    notes  = request.form.get('resolution_notes', '')
    try:
        complaint_service.update_complaint_status(complaint_id, status, notes)
        flash('Complaint status updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.complaints'))


# ── Announcements ──────────────────────────────────────────────

@admin_bp.route('/announcements')
@admin_required
def announcements():
    ann = announcement_service.get_announcements(active_only=False)
    return render_template('admin/announcements.html', announcements=ann)


@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
@admin_required
def add_announcement():
    if request.method == 'POST':
        title   = request.form.get('title','').strip()
        message = request.form.get('message','').strip()
        category= request.form.get('category','General').strip()
        expiry  = request.form.get('expiry_date','').strip() or None
        if not title or not message:
            flash('Title and message are required.', 'danger')
            return render_template('admin/add_announcement.html')
        try:
            announcement_service.create_announcement(
                title, message, category, session['user_id'], expiry
            )
            flash('Announcement created.', 'success')
            return redirect(url_for('admin.announcements'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('admin/add_announcement.html')


@admin_bp.route('/announcements/<int:ann_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_announcement(ann_id):
    ann = announcement_service.get_announcement_by_id(ann_id)
    if not ann:
        flash('Announcement not found.', 'danger')
        return redirect(url_for('admin.announcements'))
    if request.method == 'POST':
        try:
            announcement_service.update_announcement(
                ann_id,
                request.form.get('title','').strip(),
                request.form.get('message','').strip(),
                request.form.get('category','General').strip(),
                request.form.get('expiry_date','').strip() or None
            )
            flash('Announcement updated.', 'success')
            return redirect(url_for('admin.announcements'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('admin/edit_announcement.html', ann=ann)


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@admin_required
def delete_announcement(ann_id):
    try:
        announcement_service.delete_announcement(ann_id)
        flash('Announcement deleted.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.announcements'))


# ── Reports ────────────────────────────────────────────────────

@admin_bp.route('/reports')
@admin_required
def reports():
    stats           = _get_stats()
    complaint_chart = complaint_service.get_complaint_chart()
    all_students    = student_service.get_all_students()
    all_rooms       = room_service.get_all_rooms()
    return render_template('admin/reports.html',
        stats=stats, complaint_chart=complaint_chart,
        all_students=all_students, all_rooms=all_rooms)


# ── Admin Management ───────────────────────────────────────────

@admin_bp.route('/admins')
@admin_required
def admins():
    """List all admin accounts."""
    all_admins = db.fetchall(
        "SELECT user_id, full_name, email, phone, is_active, created_at "
        "FROM Users WHERE role='admin' ORDER BY created_at DESC"
    )
    return render_template('admin/admins.html', admins=all_admins)


@admin_bp.route('/admins/add', methods=['GET', 'POST'])
@admin_required
def add_admin():
    """Create a new admin account."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        phone     = request.form.get('phone', '').strip() or None
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')
        if not all([full_name, email, password]):
            flash('Full name, email and password are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            try:
                existing = auth_service.get_user_by_email(email)
                if existing:
                    flash('An account with this email already exists.', 'danger')
                else:
                    auth_service.create_user(email, password, full_name,
                                             role='admin', phone=phone)
                    flash(f'Admin account for {full_name} created successfully.', 'success')
                    return redirect(url_for('admin.admins'))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    return render_template('admin/add_admin.html')


@admin_bp.route('/admins/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    """Activate / deactivate an admin account (cannot deactivate yourself)."""
    if user_id == session['user_id']:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.admins'))
    admin_user = db.fetchone("SELECT * FROM Users WHERE user_id=? AND role='admin'", (user_id,))
    if not admin_user:
        flash('Admin not found.', 'danger')
        return redirect(url_for('admin.admins'))
    new_status = 0 if admin_user['is_active'] else 1
    db.execute("UPDATE Users SET is_active=? WHERE user_id=?", (new_status, user_id))
    flash('Admin status updated.', 'success')
    return redirect(url_for('admin.admins'))
