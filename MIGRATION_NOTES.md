# CID Database Migration Notes

## Branch: feature/database-migration
**Started:** 2025-09-05
**Author:** Fernando Ortega

## Objective
Migrate CID from JSON file storage to PostgreSQL database (Supabase)

## Current State (Original)
CID currently uses JSON files for data persistence:
- `backend/infra/data/app_data/*.json` - Application data
- `backend/infra/data/keys/` - JWT signing keys
- File-based storage for all entities

## Target State
- PostgreSQL database (Supabase) for all data
- Proper tables with relationships
- Database migrations
- Connection pooling
- Transaction support

## Migration Plan

### Phase 1: Database Schema Design
- [ ] Design tables for all entities
- [ ] Create migration scripts
- [ ] Set up Supabase connection

### Phase 2: Backend Services Migration
- [ ] Migrate JWT/Auth services
- [ ] Migrate User/Role services  
- [ ] Migrate Permission services
- [ ] Migrate Application registration
- [ ] Migrate Token templates

### Phase 3: Testing & Validation
- [ ] Unit tests for database layer
- [ ] Integration tests
- [ ] Data migration scripts
- [ ] Rollback procedures

## Changes Tracking

### Files Modified
<!-- List files as you modify them -->

### Files Added
- `MIGRATION_NOTES.md` - This documentation

### Dependencies Added
<!-- List new dependencies -->

## Commands & Configuration

### Database Connection
```bash
# Supabase PostgreSQL
Host: supabase_db_mi-proyecto-supabase
Port: 5432
Database: postgres
User: postgres
Password: your-super-secret-and-long-postgres-password
```

### Docker Setup
```bash
# To be configured
```

## Notes
- All changes are in branch `feature/database-migration`
- Original code remains in `main` branch
- Use `git diff main` to see all changes