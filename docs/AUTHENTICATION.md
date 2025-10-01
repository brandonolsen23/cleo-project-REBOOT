# Cleo Authentication System

This document describes the authentication and authorization system implemented for the Cleo real estate data platform.

## Overview

The Cleo authentication system uses **Supabase Authentication** with **Row Level Security (RLS)** to provide secure access control for the application. The system supports three user roles with different permission levels.

## Architecture

### Components

1. **Supabase Auth** - Handles user authentication, session management, and JWT tokens
2. **User Profiles** - Extended user information with roles and permissions
3. **Row Level Security (RLS)** - Database-level access control
4. **Frontend Components** - React/Next.js authentication UI
5. **Python Backend** - Service authentication for data processing scripts

### User Roles

| Role | Permissions | Description |
|------|-------------|-------------|
| `admin` | Full access | Can manage users, view/edit all data, access admin panel |
| `analyst` | Data management | Can view and edit properties, transactions, notes |
| `viewer` | Read-only | Can view data but cannot make changes |

## Database Schema

### User Profiles Table

```sql
CREATE TABLE public.user_profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT,
  full_name TEXT,
  avatar_url TEXT,
  role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'viewer')),
  organization TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Row Level Security Policies

All business tables (properties, transactions, owners, brands, etc.) have RLS enabled with the following policies:

- **Viewers and above**: Can read all data
- **Analysts and above**: Can create, update, and delete data
- **Admins**: Full access to all operations

## Setup Instructions

### 1. Environment Configuration

Create a `.env` file with the following variables:

```bash
# Database
DATABASE_URL=your-supabase-postgres-connection-string

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Frontend
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
```

### 2. Apply Authentication Schema

Run the authentication setup script:

```bash
cd scripts/setup
python setup_auth.py
```

This script will:
- Apply the authentication schema to your database
- Enable RLS on all business tables
- Create the first admin user (interactive)
- Verify the setup

### 3. Frontend Setup

Install dependencies and start the development server:

```bash
cd webapp/frontend
npm install
npm run dev
```

Visit `http://localhost:3000/login` to access the application.

## Frontend Usage

### Authentication Components

#### LoginForm
```tsx
import LoginForm from '@/components/auth/LoginForm'

export default function LoginPage() {
  return <LoginForm />
}
```

#### Protected Routes
```tsx
import ProtectedRoute from '@/components/auth/ProtectedRoute'

export default function AdminPage() {
  return (
    <ProtectedRoute requiredRole="admin">
      <AdminContent />
    </ProtectedRoute>
  )
}
```

#### User Menu
```tsx
import UserMenu from '@/components/auth/UserMenu'

export default function Layout({ user }) {
  return (
    <nav>
      <UserMenu user={user} />
    </nav>
  )
}
```

### Middleware Protection

The application uses Next.js middleware to protect routes:

```typescript
// middleware.ts
export async function middleware(req: NextRequest) {
  // Automatic route protection based on authentication status
  // and user roles
}
```

Protected routes:
- `/dashboard/*` - Requires authentication
- `/admin/*` - Requires admin role
- `/login`, `/signup` - Redirects authenticated users to dashboard

## Python Backend Usage

### Service Authentication

For background scripts and data processing:

```python
from common.auth import get_auth_client
from common.db import connect_with_service_role

# Service role connection (bypasses RLS)
conn = connect_with_service_role()

# Create users programmatically
auth_client = get_auth_client()
user = auth_client.create_user(
    email="user@example.com",
    password="secure_password",
    user_metadata={"full_name": "John Doe"}
)
```

### User Context Queries

For API endpoints that need to respect user permissions:

```python
from common.db import execute_with_user_context
from common.auth import require_role

# Verify user has required role
user = require_role(token, 'analyst')

# Execute query with user context
results = execute_with_user_context(
    "SELECT * FROM properties WHERE city = %s",
    params=('Toronto',),
    user_id=user['id']
)
```

### CLI User Management

```bash
# Create admin user
python common/auth.py create-admin user@example.com password123 "John Doe"

# List all users
python common/auth.py list-users

# Get specific user
python common/auth.py get-user <user-id>
```

## Security Features

### Password Requirements
- Minimum 8 characters
- Handled by Supabase Auth with industry standards

### Session Management
- JWT tokens with automatic refresh
- Secure session storage in browser
- Server-side session validation

### Row Level Security
- Database-level access control
- Cannot be bypassed by application bugs
- Policies enforce role-based permissions

### API Security
- All API routes protected by middleware
- Token validation on every request
- Role verification for sensitive operations

## Development Workflow

### Testing Authentication

1. **Setup Test Environment**
   ```bash
   SKIP_ADMIN_SETUP=true python scripts/setup/setup_auth.py
   ```

2. **Create Test Users**
   ```python
   # Create users with different roles for testing
   create_admin_user("admin@test.com", "password123", "Test Admin")
   auth_client.create_user("analyst@test.com", "password123")
   auth_client.update_user_role(user_id, "analyst")
   ```

3. **Test Role Permissions**
   - Login with different roles
   - Verify access to appropriate features
   - Test unauthorized access handling

### Common Issues

#### RLS Policies Not Working
- Ensure `auth.uid()` context is set properly
- Check that policies are applied to correct tables
- Verify user has correct role in user_profiles table

#### Frontend Authentication Errors
- Check environment variables are set correctly
- Verify Supabase project configuration
- Ensure middleware is configured properly

#### Python Backend Issues
- Confirm service role key has proper permissions
- Check that .env file is loaded correctly
- Verify database connection strings

## API Reference

### Authentication Endpoints

Supabase provides these endpoints automatically:

- `POST /auth/v1/signup` - User registration
- `POST /auth/v1/token` - Sign in
- `POST /auth/v1/logout` - Sign out
- `GET /auth/v1/user` - Get current user
- `PUT /auth/v1/user` - Update user

### Custom API Functions

Database functions available for frontend use:

- `get_user_role()` - Returns current user's role
- `is_admin()` - Returns true if current user is admin

## Future Enhancements

### Planned Features
- [ ] Email verification
- [ ] Password reset flow
- [ ] Multi-factor authentication
- [ ] OAuth providers (Google, Microsoft)
- [ ] Audit logging
- [ ] Session management dashboard
- [ ] API rate limiting
- [ ] Role-based data filtering

### Security Improvements
- [ ] IP-based access restrictions
- [ ] Failed login attempt monitoring
- [ ] Suspicious activity detection
- [ ] Regular security audits

## Support

For authentication-related issues:

1. Check the application logs for error messages
2. Verify environment configuration
3. Test with a fresh browser session
4. Confirm user roles in the database
5. Contact system administrator if issues persist