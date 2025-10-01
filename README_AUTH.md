# Cleo Authentication Quick Start

This guide will help you set up authentication for the Cleo project in under 10 minutes.

## Prerequisites

- Supabase project created
- Environment variables configured
- Python 3.10+ and Node.js 18+

## Step 1: Configure Environment

Copy the example environment file and fill in your Supabase credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase project details:

```bash
# Database
DATABASE_URL=your-supabase-postgres-connection-string

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Authentication
NEXTAUTH_SECRET=your-random-secret-string
NEXTAUTH_URL=http://localhost:3000
```

## Step 2: Install Dependencies

Install Python dependencies:

```bash
pip install -r scripts/setup/requirements.txt
```

Install frontend dependencies:

```bash
cd webapp/frontend
npm install
cd ../..
```

## Step 3: Set Up Authentication

Run the authentication setup script:

```bash
python scripts/setup/setup_auth.py
```

This will:
- Apply the authentication schema to your database
- Enable Row Level Security (RLS)
- Create your first admin user (interactive prompt)
- Verify the setup

## Step 4: Test the Setup

Run the test suite to verify everything is working:

```bash
python scripts/setup/test_auth.py
```

## Step 5: Start the Frontend

```bash
cd webapp/frontend
npm run dev
```

Visit http://localhost:3000/login and sign in with your admin credentials!

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access - manage users, edit all data |
| **Analyst** | Can view and edit properties/transactions |
| **Viewer** | Read-only access to data |

## Quick Commands

### Create Users

```bash
# Create admin user
python common/auth.py create-admin user@example.com password123 "Full Name"

# List all users
python common/auth.py list-users
```

### Frontend Development

```bash
# Start development server
cd webapp/frontend && npm run dev

# Build for production
cd webapp/frontend && npm run build
```

### Python Scripts

All data ingestion scripts now use service role authentication automatically:

```bash
# Realtrack ingestion (example)
python scripts/scraper/realtrack_ingest.py --input data.json
```

## Troubleshooting

### Authentication Not Working

1. **Check environment variables**: Run `python scripts/setup/test_auth.py`
2. **Verify Supabase settings**: Ensure RLS is enabled in your Supabase dashboard
3. **Clear browser data**: Try an incognito window

### Permission Errors

1. **Check user role**: Verify user has correct role in user_profiles table
2. **Test with admin user**: Admin users bypass most restrictions
3. **Check RLS policies**: Ensure policies are applied correctly

### Database Connection Issues

1. **Verify DATABASE_URL**: Test connection with `psql $DATABASE_URL`
2. **Check firewall**: Ensure your IP is allowed in Supabase
3. **Service role key**: Verify SUPABASE_SERVICE_ROLE_KEY is correct

## Next Steps

1. **Customize roles**: Modify role permissions in `config/supabase/auth_setup.sql`
2. **Add OAuth**: Configure Google/GitHub login in Supabase dashboard
3. **Deploy**: Use the frontend deployment guides for production

## Support

- 📖 Full documentation: `docs/AUTHENTICATION.md`
- 🧪 Test suite: `python scripts/setup/test_auth.py`
- 🔧 Setup script: `python scripts/setup/setup_auth.py`

## Security Notes

- Never commit `.env` files to version control
- Use strong passwords for admin accounts
- Regularly rotate service role keys
- Monitor authentication logs in Supabase dashboard