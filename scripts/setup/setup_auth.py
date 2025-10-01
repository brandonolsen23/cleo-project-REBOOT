#!/usr/bin/env python3
"""
Setup script for Cleo authentication system.
This script initializes the authentication schema and creates the first admin user.
"""

import os
import sys
import getpass
from dotenv import load_dotenv

# Add the project root to the path so we can import common modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from common.db import connect_with_retries
from common.auth import create_admin_user

load_dotenv()


def apply_auth_schema():
    """Apply the authentication schema to the database."""
    print("🔧 Applying authentication schema...")

    # Read the auth schema SQL file
    auth_schema_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'config', 'supabase', 'auth_setup.sql'
    )

    if not os.path.exists(auth_schema_path):
        print(f"❌ Error: Auth schema file not found at {auth_schema_path}")
        sys.exit(1)

    with open(auth_schema_path, 'r') as f:
        schema_sql = f.read()

    # Apply the schema
    try:
        conn = connect_with_retries()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        conn.close()
        print("✅ Authentication schema applied successfully")
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        sys.exit(1)


def create_first_admin():
    """Create the first admin user interactively."""
    print("\n👤 Creating first admin user...")

    # Check if we should skip interactive setup
    if os.getenv("SKIP_ADMIN_SETUP") == "true":
        print("⏭️  Skipping admin user creation (SKIP_ADMIN_SETUP=true)")
        return

    try:
        # Get admin user details
        print("\nPlease provide details for the first admin user:")
        email = input("Email: ").strip()

        if not email:
            print("❌ Email is required")
            sys.exit(1)

        password = getpass.getpass("Password: ").strip()

        if not password:
            print("❌ Password is required")
            sys.exit(1)

        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            sys.exit(1)

        full_name = input("Full Name: ").strip()

        if not full_name:
            full_name = email.split('@')[0].title()

        # Create the admin user
        user_id = create_admin_user(email, password, full_name)
        print(f"✅ Admin user created successfully with ID: {user_id}")

    except KeyboardInterrupt:
        print("\n⏹️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)


def verify_setup():
    """Verify that the authentication setup is working."""
    print("\n🔍 Verifying authentication setup...")

    try:
        conn = connect_with_retries()
        with conn.cursor() as cur:
            # Check if user_profiles table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'user_profiles'
                );
            """)

            if not cur.fetchone()[0]:
                print("❌ user_profiles table not found")
                return False

            # Check if RLS is enabled on user_profiles
            cur.execute("""
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'user_profiles'
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
            """)

            result = cur.fetchone()
            if not result or not result[0]:
                print("❌ RLS not enabled on user_profiles table")
                return False

            # Check if we have any admin users
            cur.execute("SELECT COUNT(*) FROM user_profiles WHERE role = 'admin';")
            admin_count = cur.fetchone()[0]

            print(f"✅ Authentication setup verified")
            print(f"   - user_profiles table exists")
            print(f"   - RLS is enabled")
            print(f"   - {admin_count} admin user(s) found")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error verifying setup: {e}")
        return False


def main():
    print("🚀 Setting up Cleo Authentication System")
    print("=" * 50)

    # Check environment variables
    required_vars = ['DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and try again.")
        sys.exit(1)

    # Apply authentication schema
    apply_auth_schema()

    # Create first admin user
    create_first_admin()

    # Verify setup
    if verify_setup():
        print("\n🎉 Authentication setup completed successfully!")
        print("\nNext steps:")
        print("1. Start your frontend: cd webapp/frontend && npm run dev")
        print("2. Visit http://localhost:3000/login to sign in")
        print("3. Use the admin user credentials you just created")
    else:
        print("\n❌ Setup verification failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()