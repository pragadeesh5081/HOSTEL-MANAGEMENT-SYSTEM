from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services import auth_service, student_service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.index'))
    error = None
    if request.method == 'POST':
        email       = request.form.get('email', '').strip()
        password    = request.form.get('password', '')
        chosen_role = request.form.get('role', 'student')   # tab selected by user
        if not email or not password:
            error = 'Email and password are required.'
        else:
            user = auth_service.get_user_by_email(email)
            if user and auth_service.verify_password(user, password):
                if not user['is_active']:
                    error = 'Your account has been deactivated. Contact admin.'
                elif user['role'] != chosen_role:
                    # Role mismatch — give a friendly but safe error
                    if chosen_role == 'admin':
                        error = 'This account is not an admin account. Please use the Student tab.'
                    else:
                        error = 'This is an admin account. Please use the Admin tab to sign in.'
                else:
                    session['user_id'] = user['user_id']
                    session['role']    = user['role']
                    session['name']    = user['full_name']
                    flash(f"Welcome back, {user['full_name']}!", 'success')
                    if user['role'] == 'admin':
                        return redirect(url_for('admin.dashboard'))
                    return redirect(url_for('student.dashboard'))
            else:
                error = 'Invalid email or password.'
    return render_template('auth/login.html', error=error)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('auth.index'))
    error = None
    if request.method == 'POST':
        role       = request.form.get('role', 'student')
        full_name  = request.form.get('full_name', '').strip()
        email      = request.form.get('email', '').strip()
        phone      = request.form.get('phone', '').strip() or None
        password   = request.form.get('password', '')
        confirm    = request.form.get('confirm_password', '')
        reg_num    = request.form.get('registration_number', '').strip()
        department = request.form.get('department', '').strip() or None
        acad_year  = request.form.get('academic_year', '').strip() or None

        if role == 'admin':
            if not all([full_name, email, password]):
                error = 'Full name, email, and password are required.'
            elif password != confirm:
                error = 'Passwords do not match.'
            elif len(password) < 6:
                error = 'Password must be at least 6 characters.'
            else:
                try:
                    auth_service.register_admin(email, password, full_name, phone=phone)
                    flash('Admin account created! Please sign in.', 'success')
                    return redirect(url_for('auth.login', role='admin'))
                except ValueError as e:
                    error = str(e)
                except Exception as e:
                    error = f'Registration failed: {e}'
        else:
            if not all([full_name, email, password, reg_num]):
                error = 'Full name, email, password, and registration number are required.'
            elif password != confirm:
                error = 'Passwords do not match.'
            elif len(password) < 6:
                error = 'Password must be at least 6 characters.'
            else:
                try:
                    auth_service.register_student(
                        email, password, full_name, reg_num,
                        phone=phone, department=department, academic_year=acad_year
                    )
                    flash('Student account created! Please sign in.', 'success')
                    return redirect(url_for('auth.login', role='student'))
                except ValueError as e:
                    error = str(e)
                except Exception as e:
                    error = f'Registration failed: {e}'
    return render_template('auth/register.html', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
