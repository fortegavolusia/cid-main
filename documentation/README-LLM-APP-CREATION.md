# LLM App Creation Flow - Services Portal to Supabase

## Overview
This document describes the flow for creating applications through the LLM chat interface in the Services Portal, which connects to the UUID Service to store apps in Supabase.

## Architecture Flow

```
User (Services Portal) 
    ↓ (Chat message)
Services Portal LLM Area
    ↓ (HTTP POST /llm/command)
UUID Service
    ↓ (Creates app with unique ID)
    ↓ (Stores in local tracking DB)
    ↓ (Stores in Supabase for persistence)
Services Portal
    ↓ (Refreshes app list)
User sees new app
```

## Components

### 1. Services Portal - Dashboard Component
- **Location**: `services-portal/src/components/Dashboard.tsx`
- **Features**:
  - LLM chat interface (lines 563-599)
  - Handles app creation commands in Spanish and English
  - Fetches apps from UUID Service
  - Displays Supabase-stored apps alongside CID-registered apps

### 2. UUID Service - LLM Handler
- **Location**: `uuid-service/src/main.py` and `uuid-service/src/llm_handler.py`
- **Endpoints**:
  - `POST /llm/command` - Process LLM commands for app creation
  - `GET /apps` - List applications from Supabase
  - `GET /apps/{app_id}` - Get specific app details
  - `PUT /apps/{app_id}` - Update app information
  - `DELETE /apps/{app_id}` - Soft delete app

### 3. Supabase Integration
- **Table**: `public.applications`
- **Fields**:
  - `id` - Unique app ID (format: app_xxxxxx)
  - `name` - Application name
  - `type` - App type (inventory, hr, finance, etc.)
  - `description` - App description
  - `created_by` - User email who created it
  - `created_at` - Creation timestamp
  - `logo_url` - Optional logo URL
  - `metadata` - JSON metadata

## Testing Instructions

### 1. Start Services
```bash
# Using the test docker-compose
docker-compose -f docker-compose-test-llm.yml up -d

# Or start services individually:
# Start PostgreSQL/Supabase
docker-compose up -d postgres

# Start UUID Service
cd uuid-service
uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload

# Start Services Portal
cd services-portal
npm run dev
```

### 2. Test App Creation Flow

1. **Open Services Portal**
   - Navigate to http://localhost:4000
   - Log in if authentication is enabled

2. **Use the LLM Chat**
   - Find the chat area on the right side of the dashboard
   - Type commands in English or Spanish:

   **Spanish examples:**
   - "Crea una app para gestión de inventarios"
   - "Necesito una aplicación de recursos humanos"
   - "Quiero una app para control financiero"

   **English examples:**
   - "Create an app for inventory management"
   - "I need a human resources application"
   - "Build a finance tracking app"

3. **Verify App Creation**
   - The chat will respond with the app details including the generated ID
   - The app list will automatically refresh
   - New app appears in "Available Applications" section

### 3. API Testing with cURL

```bash
# Create an app via LLM endpoint
curl -X POST http://localhost:8002/llm/command \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Create an app for inventory management",
    "user_email": "test@example.com"
  }'

# List all apps
curl http://localhost:8002/apps

# List apps for specific user
curl "http://localhost:8002/apps?created_by=test@example.com"

# Get specific app details
curl http://localhost:8002/apps/app_123456

# Update app
curl -X PUT http://localhost:8002/apps/app_123456 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Inventory System",
    "description": "Enhanced inventory management system"
  }'
```

## Environment Variables

### UUID Service
```env
UUID_DB_HOST=localhost
UUID_DB_PORT=54322
UUID_DB_NAME=postgres
UUID_DB_USER=postgres
UUID_DB_PASSWORD=postgres
```

### Services Portal
```env
VITE_API_ORIGIN=http://localhost:8001
VITE_UUID_SERVICE=http://localhost:8002
```

## Troubleshooting

### Issue: Apps not appearing in dashboard
- Check UUID Service is running: `curl http://localhost:8002/`
- Check PostgreSQL connection: `docker logs supabase_postgres`
- Verify CORS settings in UUID Service

### Issue: Chat not responding
- Check browser console for errors
- Verify UUID Service endpoint is accessible
- Check network tab for failed requests

### Issue: Database errors
- Ensure PostgreSQL is running
- Check database exists: `docker exec -it supabase_postgres psql -U postgres -c "\l"`
- Verify tables are created: Check UUID Service logs on startup

## Next Steps

1. **Register apps in CID**: After creation, apps should be registered in CID for permission management
2. **Add logo upload**: Implement logo upload functionality for created apps
3. **Add app templates**: Create pre-defined templates for common app types
4. **Implement app launch**: Add actual app launching functionality
5. **Add app deletion**: Implement proper app deletion workflow

## Security Considerations

- Validate user authentication before allowing app creation
- Implement rate limiting on LLM endpoint
- Sanitize app names and descriptions
- Add permission checks for app management
- Implement audit logging for all app operations