from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.decorators import student_required
from services import (student_service, room_service, leave_service,
                      complaint_service, announcement_service, auth_service)

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@student_required
def dashboard():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    sid = student['student_id']
    allocation   = room_service.get_active_allocation(sid)
    my_leaves    = leave_service.get_leaves(sid)
    my_complaints= complaint_service.get_complaints(sid)
    recent_changes= room_service.get_change_requests(sid)[:3]
    announcements= announcement_service.get_announcements(active_only=True)[:5]
    pending_leaves = sum(1 for l in my_leaves if l['status'] == 'Pending')
    open_complaints= sum(1 for c in my_complaints if c['status'] in ('Submitted','In Progress'))
    return render_template('student/dashboard.html',
        student=student, allocation=allocation,
        pending_leaves=pending_leaves,
        open_complaints=open_complaints,
        recent_leaves=my_leaves[:4],
        recent_complaints=my_complaints[:4],
        recent_changes=recent_changes,
        announcements=announcements,
        total_leaves=len(my_leaves),
        total_complaints=len(my_complaints),
        total_announcements=len(announcements)
    )



@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    if request.method == 'POST':
        try:
            student_service.update_student_profile(
                student['student_id'],
                request.form.get('department','').strip(),
                request.form.get('academic_year','').strip(),
                request.form.get('guardian_name','').strip(),
                request.form.get('guardian_phone','').strip(),
                request.form.get('address','').strip(),
                request.form.get('full_name','').strip(),
                request.form.get('phone','').strip()
            )
            session['name'] = request.form.get('full_name','').strip()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('student.profile'))
        except Exception as e:
            flash(f'Update failed: {e}', 'danger')
    return render_template('student/profile.html', student=student)


@student_bp.route('/my-room')
@student_required
def my_room():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    allocation = room_service.get_active_allocation(student['student_id'])
    change_requests = room_service.get_change_requests(student['student_id'])
    return render_template('student/my_room.html',
        student=student, allocation=allocation, change_requests=change_requests)


@student_bp.route('/room-change-request', methods=['GET', 'POST'])
@student_required
def room_change_request():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    allocation = room_service.get_active_allocation(student['student_id'])
    if not allocation:
        flash('You must have an active room allocation to request a change.', 'warning')
        return redirect(url_for('student.my_room'))
    available_rooms = [r for r in room_service.get_all_rooms()
                       if r['status'] == 'Available' and r['room_id'] != allocation['room_id']]
    if request.method == 'POST':
        requested_room_id = request.form.get('requested_room_id')
        reason = request.form.get('reason', '').strip()
        if not requested_room_id or not reason:
            flash('Please select a room and provide a reason.', 'danger')
        else:
            try:
                room_service.submit_change_request(
                    student['student_id'], allocation['room_id'],
                    int(requested_room_id), reason
                )
                flash('Room change request submitted.', 'success')
                return redirect(url_for('student.my_room'))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    return render_template('student/room_change_request.html',
        student=student, allocation=allocation, available_rooms=available_rooms)


@student_bp.route('/apply-leave', methods=['GET', 'POST'])
@student_required
def apply_leave():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    if request.method == 'POST':
        start_date = request.form.get('start_date','').strip()
        end_date   = request.form.get('end_date','').strip()
        destination= request.form.get('destination','').strip()
        reason     = request.form.get('reason','').strip()
        emergency  = request.form.get('emergency_contact','').strip()
        if not all([start_date, end_date, destination, reason, emergency]):
            flash('All fields are required.', 'danger')
        elif end_date < start_date:
            flash('End date cannot be before start date.', 'danger')
        else:
            try:
                leave_service.submit_leave(
                    student['student_id'], start_date, end_date,
                    destination, reason, emergency
                )
                flash('Leave application submitted.', 'success')
                return redirect(url_for('student.leave_history'))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    return render_template('student/apply_leave.html', student=student)



@student_bp.route('/leave-history')
@student_required
def leave_history():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    leaves  = leave_service.get_leaves(student['student_id'])
    return render_template('student/leave_history.html', student=student, leaves=leaves)


@student_bp.route('/submit-complaint', methods=['GET', 'POST'])
@student_required
def submit_complaint():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    if request.method == 'POST':
        title       = request.form.get('title','').strip()
        category    = request.form.get('category','').strip()
        description = request.form.get('description','').strip()
        priority    = request.form.get('priority','Medium').strip()
        if not all([title, category, description]):
            flash('Title, category, and description are required.', 'danger')
        else:
            try:
                complaint_service.submit_complaint(
                    student['student_id'], title, category, description, priority
                )
                flash('Complaint submitted successfully.', 'success')
                return redirect(url_for('student.my_complaints'))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    return render_template('student/submit_complaint.html', student=student)


@student_bp.route('/my-complaints')
@student_required
def my_complaints():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    complaints = complaint_service.get_complaints(student['student_id'])
    return render_template('student/my_complaints.html', student=student, complaints=complaints)


@student_bp.route('/announcements')
@student_required
def announcements():
    user_id = session['user_id']
    student = student_service.get_student_by_user_id(user_id)
    if not student:
        flash('Student profile not found. Contact admin.', 'warning')
        return redirect(url_for('auth.logout'))
    ann = announcement_service.get_announcements(active_only=True)
    return render_template('student/announcements.html', student=student, announcements=ann)
