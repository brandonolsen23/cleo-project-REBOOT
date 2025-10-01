"""
Authentication utilities for Cleo using Supabase Auth.
Handles service account authentication for Python backend operations.
"""

import os
from typing import Optional, Dict, Any
import requests
import json
from datetime import datetime, timedelta


class SupabaseAuth:
    """Supabase authentication client for Python backend operations."""

    def __init__(self, url: Optional[str] = None, service_key: Optional[str] = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.url or not self.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.auth_url = f"{self.url}/auth/v1"
        self.rest_url = f"{self.url}/rest/v1"

        # Service role headers for bypass RLS operations
        self.service_headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    def create_user(self, email: str, password: str,
                   user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new user with email/password (admin operation)."""
        payload = {
            "email": email,
            "password": password,
            "email_confirm": True  # Auto-confirm for admin creation
        }

        if user_metadata:
            payload["user_metadata"] = user_metadata

        response = requests.post(
            f"{self.auth_url}/admin/users",
            headers=self.service_headers,
            json=payload
        )

        if response.status_code != 200:
            raise Exception(f"Failed to create user: {response.text}")

        return response.json()

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID (admin operation)."""
        response = requests.get(
            f"{self.auth_url}/admin/users/{user_id}",
            headers=self.service_headers
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get user: {response.text}")

        return response.json()

    def update_user_role(self, user_id: str, role: str) -> bool:
        """Update user role in user_profiles table."""
        if role not in ['admin', 'analyst', 'viewer']:
            raise ValueError("Role must be one of: admin, analyst, viewer")

        payload = {"role": role}

        response = requests.patch(
            f"{self.rest_url}/user_profiles",
            headers={**self.service_headers, "Prefer": "return=minimal"},
            params={"id": f"eq.{user_id}"},
            json=payload
        )

        return response.status_code == 204

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user ID."""
        response = requests.get(
            f"{self.rest_url}/user_profiles",
            headers=self.service_headers,
            params={"id": f"eq.{user_id}"}
        )

        if response.status_code == 200:
            profiles = response.json()
            return profiles[0] if profiles else None

        return None

    def list_users(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """List all users (admin operation)."""
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(
            f"{self.auth_url}/admin/users",
            headers=self.service_headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(f"Failed to list users: {response.text}")

        return response.json()

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return user info."""
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(
            f"{self.auth_url}/user",
            headers=headers
        )

        if response.status_code == 200:
            return response.json()

        return None

    def delete_user(self, user_id: str) -> bool:
        """Delete a user (admin operation)."""
        response = requests.delete(
            f"{self.auth_url}/admin/users/{user_id}",
            headers=self.service_headers
        )

        return response.status_code == 200


def get_auth_client() -> SupabaseAuth:
    """Get a configured Supabase auth client."""
    return SupabaseAuth()


def require_auth(token: str) -> Dict[str, Any]:
    """
    Middleware function to verify authentication token.
    Returns user info if valid, raises exception if not.
    """
    auth_client = get_auth_client()
    user = auth_client.verify_token(token)

    if not user:
        raise Exception("Invalid or expired token")

    return user


def require_role(token: str, required_role: str) -> Dict[str, Any]:
    """
    Middleware function to verify user has required role.
    Returns user info if authorized, raises exception if not.
    """
    user = require_auth(token)
    auth_client = get_auth_client()

    profile = auth_client.get_user_profile(user['id'])

    if not profile:
        raise Exception("User profile not found")

    user_role = profile.get('role', 'viewer')

    # Role hierarchy: admin > analyst > viewer
    role_hierarchy = {'admin': 3, 'analyst': 2, 'viewer': 1}

    if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
        raise Exception(f"Insufficient permissions. Required: {required_role}, User has: {user_role}")

    return {**user, 'profile': profile}


# Example usage functions for scripts
def create_admin_user(email: str, password: str, full_name: str) -> str:
    """Create an admin user for initial setup."""
    auth_client = get_auth_client()

    user = auth_client.create_user(
        email=email,
        password=password,
        user_metadata={"full_name": full_name}
    )

    # Update role to admin
    auth_client.update_user_role(user['id'], 'admin')

    print(f"Created admin user: {email} with ID: {user['id']}")
    return user['id']


if __name__ == "__main__":
    # CLI interface for user management
    import sys

    if len(sys.argv) < 2:
        print("Usage: python auth.py <command> [args...]")
        print("Commands:")
        print("  create-admin <email> <password> <full_name>")
        print("  list-users")
        print("  get-user <user_id>")
        sys.exit(1)

    command = sys.argv[1]
    auth_client = get_auth_client()

    if command == "create-admin":
        if len(sys.argv) != 5:
            print("Usage: python auth.py create-admin <email> <password> <full_name>")
            sys.exit(1)
        create_admin_user(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "list-users":
        users = auth_client.list_users()
        print(json.dumps(users, indent=2))

    elif command == "get-user":
        if len(sys.argv) != 3:
            print("Usage: python auth.py get-user <user_id>")
            sys.exit(1)
        user = auth_client.get_user(sys.argv[2])
        print(json.dumps(user, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)