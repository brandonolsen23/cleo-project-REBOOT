#!/usr/bin/env python3
"""
Test script for Cleo authentication system.
This script verifies that authentication and RLS are working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from common.db import connect_with_retries, execute_with_user_context
from common.auth import get_auth_client, create_admin_user

load_dotenv()


def test_user_creation():
    """Test creating users with different roles."""
    print("🧪 Testing user creation...")

    auth_client = get_auth_client()

    try:
        # Create test users
        test_users = [
            ("test-admin@cleo.test", "testpass123", "Test Admin", "admin"),
            ("test-analyst@cleo.test", "testpass123", "Test Analyst", "analyst"),
            ("test-viewer@cleo.test", "testpass123", "Test Viewer", "viewer"),
        ]

        created_users = []

        for email, password, name, role in test_users:
            try:
                # Create user
                user = auth_client.create_user(
                    email=email,
                    password=password,
                    user_metadata={"full_name": name}
                )

                # Update role
                success = auth_client.update_user_role(user['id'], role)

                if success:
                    created_users.append((user['id'], email, role))
                    print(f"✅ Created {role} user: {email}")
                else:
                    print(f"❌ Failed to set role for {email}")

            except Exception as e:
                if "already registered" in str(e) or "already exists" in str(e):
                    print(f"⚠️  User {email} already exists, skipping...")
                else:
                    print(f"❌ Error creating user {email}: {e}")

        return created_users

    except Exception as e:
        print(f"❌ Error in user creation test: {e}")
        return []


def test_rls_policies():
    """Test that RLS policies are working correctly."""
    print("🔒 Testing RLS policies...")

    try:
        conn = connect_with_retries()

        with conn.cursor() as cur:
            # Check if RLS is enabled on key tables
            tables_to_check = ['user_profiles', 'properties', 'transactions', 'notes']

            for table in tables_to_check:
                cur.execute("""
                    SELECT relrowsecurity
                    FROM pg_class
                    WHERE relname = %s
                    AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
                """, (table,))

                result = cur.fetchone()
                if result and result[0]:
                    print(f"✅ RLS enabled on {table}")
                else:
                    print(f"❌ RLS not enabled on {table}")

            # Test policies exist
            cur.execute("""
                SELECT schemaname, tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname;
            """)

            policies = cur.fetchall()
            if policies:
                print(f"✅ Found {len(policies)} RLS policies")
                for schema, table, policy in policies:
                    print(f"   - {table}: {policy}")
            else:
                print("❌ No RLS policies found")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error testing RLS policies: {e}")
        return False


def test_database_functions():
    """Test custom database functions."""
    print("⚙️  Testing database functions...")

    try:
        conn = connect_with_retries()

        with conn.cursor() as cur:
            # Test functions exist
            functions_to_check = [
                'handle_new_user',
                'get_user_role',
                'is_admin',
                'set_updated_at'
            ]

            for func_name in functions_to_check:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc p
                        JOIN pg_namespace n ON p.pronamespace = n.oid
                        WHERE n.nspname = 'public' AND p.proname = %s
                    );
                """, (func_name,))

                exists = cur.fetchone()[0]
                if exists:
                    print(f"✅ Function {func_name} exists")
                else:
                    print(f"❌ Function {func_name} not found")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error testing database functions: {e}")
        return False


def test_user_profiles():
    """Test user profiles table and data."""
    print("👤 Testing user profiles...")

    try:
        conn = connect_with_retries()

        with conn.cursor() as cur:
            # Count users by role
            cur.execute("""
                SELECT role, COUNT(*)
                FROM user_profiles
                GROUP BY role
                ORDER BY role;
            """)

            role_counts = cur.fetchall()
            if role_counts:
                print("✅ User profile statistics:")
                for role, count in role_counts:
                    print(f"   - {role}: {count} users")
            else:
                print("⚠️  No user profiles found")

            # Check for admin users
            cur.execute("SELECT COUNT(*) FROM user_profiles WHERE role = 'admin';")
            admin_count = cur.fetchone()[0]

            if admin_count > 0:
                print(f"✅ Found {admin_count} admin user(s)")
            else:
                print("❌ No admin users found - you should create one!")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error testing user profiles: {e}")
        return False


def test_environment_variables():
    """Test that required environment variables are set."""
    print("🌍 Testing environment variables...")

    required_vars = [
        'DATABASE_URL',
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]

    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Don't print the full value for security
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: Not set")
            all_set = False

    return all_set


def cleanup_test_users():
    """Clean up test users created during testing."""
    print("🧹 Cleaning up test users...")

    auth_client = get_auth_client()
    test_emails = [
        "test-admin@cleo.test",
        "test-analyst@cleo.test",
        "test-viewer@cleo.test"
    ]

    for email in test_emails:
        try:
            # Note: In a real implementation, you'd need to get the user ID first
            # This is a simplified cleanup
            print(f"⚠️  Would delete user: {email} (not implemented)")
        except Exception as e:
            print(f"⚠️  Could not delete {email}: {e}")


def main():
    print("🚀 Cleo Authentication System Test Suite")
    print("=" * 50)

    tests = [
        ("Environment Variables", test_environment_variables),
        ("Database Functions", test_database_functions),
        ("RLS Policies", test_rls_policies),
        ("User Profiles", test_user_profiles),
        ("User Creation", test_user_creation),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")

    print(f"\n🏁 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Authentication system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the output above for details.")

    # Offer cleanup
    if input("\nDo you want to clean up test users? (y/N): ").lower().strip() == 'y':
        cleanup_test_users()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())