# Backup Status - September 8, 2025

## Working Services Status

### CID Service
- **Backend**: Running on port 8001 (healthy)
- **Frontend**: Running on port 3000 (functional, health check shows unhealthy but doesn't affect operation)
- **Database**: Connected to Supabase PostgreSQL (CIDS schema)
- **Authentication**: Azure AD integration working

### UUID Service
- **Container**: uuid-service-dev
- **Port**: 8002
- **Status**: Healthy
- **Database**: Connected to Supabase PostgreSQL (uuid_service schema)

### Ecosystem Monitor
- **Backend**: Port 5000
- **Frontend**: Port 5001
- **Status**: Running and monitoring all services

### Supabase
- **Database**: Port 54322
- **Studio**: Port 54323
- **Status**: All services running

## Backup Files Created

1. **Main Backup**: `/home/dpi/projects/CID_backup_20250908_working.tar.gz` (74MB)
   - Contains: CID/, uuid-service/, docker-compose.yml

2. **Environment Files**:
   - `/home/dpi/projects/CID/.env.backup_20250908`
   - `/home/dpi/projects/uuid-service/.env.backup_20250908`

## Key Configuration Notes

### Database Connection
- **Host**: supabase_db_mi-proyecto-supabase
- **Port**: 5432 (internal), 54322 (external)
- **Database**: postgres
- **User**: postgres
- **Password**: postgres
- **Schemas**: CIDS (for CID service), uuid_service (for UUID service)

### Important: Environment Variable Issue Fixed
- System environment variable `DB_PASSWORD` was overriding .env file
- Solution: Unset system variable before running docker-compose

### Docker Networks
- cid_cid-network
- uuid-service_uuid-network
- supabase_network_mi-proyecto-supabase (external)

## Services Dashboard Access
- CID Frontend: https://localhost:3000
- UUID Service API: http://localhost:8002
- Ecosystem Monitor: http://localhost:5001

## To Restore from Backup

```bash
# 1. Extract backup
cd /home/dpi/projects
tar -xzf CID_backup_20250908_working.tar.gz

# 2. Restore environment files
cp CID/.env.backup_20250908 CID/.env
cp uuid-service/.env.backup_20250908 uuid-service/.env

# 3. Make sure no system environment variables override
unset DB_PASSWORD

# 4. Start services
docker-compose up -d  # For CID
cd uuid-service && docker-compose up -d  # For UUID service
```

## Current Docker Containers Running
- cid-backend
- cid-frontend  
- uuid-service-dev
- ecosystem-monitor-backend
- ecosystem-monitor-frontend
- supabase_db_mi-proyecto-supabase (and other Supabase services)

## Notes
- All services are functional and stable
- Supabase integration is working correctly
- Dashboard shows correct app counts from database
- UUID service is generating IDs correctly