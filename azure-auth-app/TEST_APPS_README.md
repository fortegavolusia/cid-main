# Test Applications for Auth Service

This directory contains two test applications that demonstrate how to integrate with the centralized authentication service.

## Test Applications

### 1. Simple Flask App (`test_app.py`)
A basic Flask application that demonstrates:
- Login flow with the auth service
- Token validation
- Protected API endpoints
- Role-based access control

**Features:**
- Simple web interface
- Basic authentication flow
- Example API endpoints with role requirements

### 2. Advanced FastAPI App (`advanced_test_app.py`)
A more sophisticated FastAPI application that demonstrates:
- Modern async/await patterns
- Interactive API testing interface
- Multiple role-based endpoints
- Better session management
- Token introspection display

**Features:**
- Professional UI with API test panel
- Real-time API testing from the browser
- Multiple endpoints with different role requirements
- Detailed token information display

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements_test_apps.txt
```

### Step 2: Register the Test App

1. Login to the auth service as an admin
2. Go to Administration → App Registration
3. Register a new app with these details:
   - **Name**: Test Application (or Advanced Test App)
   - **Description**: Test app for auth integration
   - **Owner Email**: your-email@company.com
   - **Redirect URIs**: 
     - For Flask app: `http://localhost:5000/auth/callback`
     - For FastAPI app: `http://localhost:8001/auth/callback`

4. **IMPORTANT**: Save the generated Client ID and Client Secret

### Step 3: Configure the Test App

Create a `.env` file in the auth service directory:

```env
# For test apps
TEST_APP_CLIENT_ID=app_xxxxxxxxxxxxx
TEST_APP_CLIENT_SECRET=your_client_secret_here

# Optional: Auth service URL (defaults to https://localhost:8000)
AUTH_SERVICE_URL=https://localhost:8000
```

### Step 4: Set Up Role Mappings (Optional)

To test role-based access:

1. In the auth service admin panel, go to your registered app
2. Click "Role Mappings"
3. Add mappings like:
   - AD Group "YourName-TestAdmins" → Role "admin"
   - AD Group "Engineering" → Role "editor"
   - AD Group "Domain Users" → Role "viewer"

### Step 5: Run the Test App

**Flask App:**
```bash
python test_app.py
```
Access at: http://localhost:5000

**FastAPI App:**
```bash
python advanced_test_app.py
```
Access at: http://localhost:8001

## Testing the Integration

### 1. Basic Authentication Flow
1. Open the test app in your browser
2. Click "Login with Auth Service"
3. You'll be redirected to the auth service
4. Login with your Azure AD credentials
5. You'll be redirected back to the test app, now authenticated

### 2. Test API Endpoints

**Public Endpoint** (no auth required):
```bash
curl http://localhost:5000/api/public
```

**Authenticated Endpoint** (requires valid token):
```bash
curl http://localhost:5000/api/profile \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Role-Based Endpoint** (requires specific role):
```bash
curl http://localhost:5000/api/admin \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 3. Using the Advanced Test App

The FastAPI app includes an interactive API test panel:
1. Login to see your user info and roles
2. Use the "API Test Panel" to test different endpoints
3. See real-time responses and error messages
4. View your decoded token claims

## How It Works

### Authentication Flow

1. **Login Initiation**:
   - User clicks login
   - App generates state for CSRF protection
   - Redirects to auth service with client_id and redirect_uri

2. **Auth Service Login**:
   - User authenticates with Azure AD
   - Auth service validates credentials
   - Issues internal JWT token

3. **Callback Handling**:
   - Auth service redirects back with access token
   - Test app validates token with auth service
   - Stores user session

4. **API Access**:
   - Test app includes token in API requests
   - Validates token and checks roles
   - Returns appropriate response

### Token Structure

The JWT tokens include:
```json
{
  "sub": "user-azure-id",
  "email": "user@company.com",
  "name": "User Name",
  "groups": ["Engineering", "TestApp-Admins"],
  "app_roles": ["admin", "editor"],
  "client_id": "app_xxxxxxxxxxxxx",
  "exp": 1234567890
}
```

## Troubleshooting

### "App not configured" Error
- Make sure you've set `TEST_APP_CLIENT_ID` and `TEST_APP_CLIENT_SECRET` in your `.env` file

### "Invalid state parameter" Error
- This is a CSRF protection error
- Try clearing cookies and logging in again

### "Forbidden" Error on API Endpoints
- Check that you have the required role
- Verify role mappings are set up correctly in the auth service
- Check the decoded token to see what roles you have

### SSL Certificate Errors
- The test apps disable SSL verification for local development
- In production, use proper SSL certificates

## Production Considerations

These test apps are for demonstration only. For production:

1. **Enable SSL verification**
2. **Use proper session storage** (Redis, database)
3. **Add error handling and logging**
4. **Implement token refresh logic**
5. **Add CSRF protection**
6. **Use environment-specific configuration**
7. **Add rate limiting**
8. **Implement proper secret management**

## Next Steps

1. Study the code to understand the integration pattern
2. Implement similar authentication in your own apps
3. Customize the role mappings for your use case
4. Add token refresh functionality
5. Implement logout with auth service coordination