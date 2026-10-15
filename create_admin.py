"""
Create the first administrator account.
Run once to bootstrap the admin user.

Usage:
    python create_admin.py
"""
import sys
import getpass
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from models.db import init_db
from app import create_app


def main():
    app = create_app()

    print("=== Hostel Management System — Create Admin ===")
    full_name = input("Admin full name: ").strip()
    email     = input("Admin email:     ").strip()
    phone     = input("Phone (optional):").strip() or None
    password  = getpass.getpass("Password:        ")
    confirm   = getpass.getpass("Confirm password:")

    if not full_name or not email or not password:
        print("ERROR: Full name, email, and password are required.")
        sys.exit(1)

    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    with app.app_context():
        from services import auth_service
        existing = auth_service.get_user_by_email(email)
        if existing:
            print(f"ERROR: An account with email '{email}' already exists.")
            sys.exit(1)
        auth_service.create_user(email, password, full_name, role='admin', phone=phone)
        print(f"\n✓ Admin account created for '{full_name}' ({email})")
        print("  Log in at: http://localhost:5000/login")


if __name__ == '__main__':
    main()
