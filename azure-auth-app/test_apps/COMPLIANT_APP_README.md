# CIDS Compliant Test Application

## Overview

This is a fully CIDS-compliant test application that demonstrates:
- ✅ Complete discovery endpoint implementation
- ✅ API key authentication (no client_secret needed!)
- ✅ Field-level permission filtering
- ✅ Row-level security (RLS)
- ✅ Sensitive data tagging (PII, PHI, Financial)
- ✅ Audit logging
- ✅ Multiple resource types (users, orders, reports)

## Quick Start

### 1. Start CIDS Services

```bash
# Terminal 1: Start CIDS backend
cd /home/jnbailey/Desktop/CIDS/azure-auth-app
source .venv/bin/activate
DEV_CROSS_ORIGIN=true bash restart_server.sh

# Terminal 2: Start CIDS frontend
cd /home/jnbailey/Desktop/CIDS/cids-frontend
npm run dev
```

### 2. Start the Compliant App

```bash
# Terminal 3: Start the compliant test app
cd /home/jnbailey/Desktop/CIDS/azure-auth-app
source .venv/bin/activate
python test_apps/compliant_app.py
```

The app will start on http://localhost:8001

### 3. Register the App with CIDS

#### Option A: Automated Registration (Recommended)

```bash
# Run the registration script
python test_apps/register_compliant_app.py
```

This script will:
1. Register the app with CIDS
2. Create an API key
3. Save credentials to `.env`
4. Test the integration

#### Option B: Manual Registration via GUI

1. Open CIDS Admin: http://localhost:5173/admin
2. Go to "App Administration" section
3. Click "Register New App" and enter:
   - **Name**: CIDS Compliant Test App
   - **Description**: Test application demonstrating CIDS compliance
   - **Owner Email**: admin@example.com
   - **Redirect URI**: http://localhost:8001/auth/callback
   - ✅ **Allow Endpoint Discovery**: Checked
   - **Discovery Endpoint**: http://localhost:8001/discovery/endpoints

4. Click "Register App" and save the Client ID and Secret

5. Click "API Keys" button on the app card
6. Generate a new API key:
   - **Name**: Test Environment Key
   - **Permissions**: `admin` (or specific permissions)
   - **TTL**: 90 days

7. Save the API key (shown only once!)

### 4. Configure the App

Create or update `.env` file:

```bash
# /home/jnbailey/Desktop/CIDS/azure-auth-app/test_apps/.env
CIDS_API_KEY=cids_ak_...  # Your API key from step 3
CIDS_BASE_URL=http://localhost:8000
```

### 5. Test the Integration

#### Test Discovery
```bash
# Trigger discovery from CIDS
curl -X POST http://localhost:8000/discovery/endpoints/{client_id}
```

#### Test API Key Authentication
```bash
# Get users (replace with your API key)
curl -H "Authorization: Bearer cids_ak_..." \
     http://localhost:8001/api/users
```

## Available Endpoints

### Discovery
- `GET /discovery/endpoints` - CIDS discovery endpoint

### Health & Status
- `GET /` - App information
- `GET /health` - Health check

### Users Resource
- `GET /api/users` - List all users
- `GET /api/users/{user_id}` - Get specific user
- `POST /api/users` - Create user
- `PUT /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user

### Orders Resource
- `GET /api/orders` - List all orders
- `GET /api/orders/{order_id}` - Get specific order

### Reports Resource
- `GET /api/reports` - List all reports
- `GET /api/reports/{report_id}` - Get specific report

## Field Sensitivity Tags

The app demonstrates proper field tagging:

| Tag | Description | Example Fields |
|-----|-------------|----------------|
| `pii` | Personally Identifiable Information | email, name, ssn, phone, address |
| `phi` | Protected Health Information | medical_records |
| `financial` | Financial Data | salary, budget, credit_card_last4 |
| `sensitive` | General Sensitive Data | performance_rating, confidential |

## Permission Examples

### Granular Permissions
```
compliant_app.users.read           # Read user resources
compliant_app.users.read.email     # Read email field only
compliant_app.users.read.salary    # Read salary field only
compliant_app.users.read.*         # Read all user fields
compliant_app.users.write          # Write user resources
compliant_app.users.delete         # Delete users
admin                               # Full access to everything
```

### Testing Different Permission Levels

1. **Create Limited API Key** in CIDS Admin:
   - Permissions: `compliant_app.users.read, compliant_app.users.read.email, compliant_app.users.read.name`
   - This key can only see user ID, email, and name

2. **Create Admin API Key**:
   - Permissions: `admin`
   - This key can see everything

3. **Compare Responses**:
```bash
# Limited key - only sees permitted fields
curl -H "Authorization: Bearer {limited_key}" \
     http://localhost:8001/api/users/user1

# Response: {"id": "user1", "email": "...", "name": "..."}

# Admin key - sees all fields
curl -H "Authorization: Bearer {admin_key}" \
     http://localhost:8001/api/users/user1

# Response: {full user object with salary, ssn, medical_records, etc.}
```

## RLS (Row-Level Security) Testing

The app supports RLS filters. To test:

1. Configure RLS in CIDS for a role
2. Create an API key with that role
3. The app will automatically filter results based on RLS rules

Example RLS filter:
```sql
department.name = 'Engineering'  -- Only see Engineering users
user_id = @current_user_id       -- Only see own data
```

## Troubleshooting

### App won't start
- Check port 8001 is available
- Install dependencies: `pip install fastapi httpx uvicorn`

### Discovery fails
- Ensure app is running on http://localhost:8001
- Check discovery endpoint: http://localhost:8001/discovery/endpoints
- Verify CIDS can reach the app (network/firewall)

### API key not working
- Verify key format: `Bearer cids_ak_...`
- Check key hasn't expired
- Ensure key has required permissions
- Test validation: `curl -H "Authorization: Bearer {key}" http://localhost:8000/auth/validate`

### No data returned
- Check permissions for the API key
- Verify field-level permissions
- Check RLS filters aren't filtering out all data

## Architecture

```
┌─────────────────┐
│   CIDS Admin    │
│   (React UI)    │
└────────┬────────┘
         │ Register & Manage
         ▼
┌─────────────────┐
│   CIDS Backend  │
│  (FastAPI/Auth) │
└────────┬────────┘
         │ Validate API Keys
         ▼
┌─────────────────┐
│  Compliant App  │
│   (This App)    │
└─────────────────┘
```

## Key Features Demonstrated

1. **No Client Secret**: Uses API keys instead
2. **Discovery**: Full metadata about endpoints and fields
3. **Field Filtering**: Based on permissions
4. **Sensitive Data**: Proper tagging of PII/PHI/Financial
5. **Audit Logging**: All access attempts logged
6. **Multiple Resources**: Users, Orders, Reports
7. **Nested Objects**: Department within User
8. **Permission Hierarchy**: Resource → Action → Field

## Development

To modify the app:

1. Edit `compliant_app.py`
2. Update discovery endpoint with new fields/endpoints
3. Re-register or update app in CIDS
4. Run discovery to update CIDS metadata

## Support

For issues or questions:
- Check CIDS logs: `journalctl -f`
- Check app logs in terminal
- Verify API key with: `/auth/validate`
- Test discovery: `/discovery/endpoints`