# CIDS Migration Issues Report

**Date**: 2025-09-07  
**Time**: 22:00 UTC

## Migration Status

### ✅ Successfully Migrated

| Component | Count | Status | Notes |
|-----------|-------|--------|-------|
| **Schema CIDS** | 1 | ✅ Complete | Created successfully with all table structures |
| **Registered Apps** | 6 | ✅ Complete | All applications migrated to `cids.registered_apps` |
| **Token Templates** | 2 | ✅ Complete | Default Token, test 3 |
| **App Role Mappings** | 3 | ✅ Complete | AD group to role mappings |

### ❌ Migration Problems

| Component | Expected | Actual | Status | Issue |
|-----------|----------|--------|--------|-------|
| **Roles** | 4 | 0 | ❌ Failed | Rollback due to foreign key error |
| **Permissions** | Unknown | 0 | ❌ Failed | Dependent on roles migration |
| **Discovered Permissions** | Unknown | 0 | ⚠️ Empty | May not have had data to migrate |

## Root Cause Analysis

### Primary Issue: Foreign Key Constraint Violation
```
Error: test_app/test_role
insert or update on table "roles" violates foreign key constraint "roles_client_id_fkey"
DETAIL: Key (client_id)=(test_app) is not present in table "registered_apps"
```

### Problem Description
- The `role_permissions.json` file contains a role for `test_app`
- No application with client_id `test_app` exists in `registered_apps.json`
- This orphaned reference causes the roles migration to fail
- When the error occurs, PostgreSQL rolls back ALL role insertions (transaction rollback)

### Impact
- 4 valid roles were attempted but none were saved due to rollback
- Permissions depend on roles, so they also failed
- This creates a cascade failure for role-dependent data

## Data Integrity Check

### Valid Data
- All 6 registered applications have valid structure
- Token templates are independent and migrated successfully
- App role mappings reference existing applications

### Invalid Data
- `test_app` role exists without corresponding application
- Need to clean orphaned references in `role_permissions.json`

## Recommended Solutions

1. **Option A: Clean Source Data**
   - Remove `test_app` entries from `role_permissions.json`
   - Re-run migration with clean data

2. **Option B: Modify Migration Script**
   - Add validation to skip orphaned roles
   - Use individual transactions per role (no bulk rollback)
   - Log skipped items for review

3. **Option C: Create Missing Application**
   - Add `test_app` to `registered_apps.json`
   - Maintain referential integrity

## Current Database State

```sql
Schema: cids
Tables created: All structures present
Data status:
- cids.registered_apps: 6 records ✅
- cids.roles: 0 records ❌
- cids.permissions: 0 records ❌
- cids.token_templates: 2 records ✅
- cids.app_role_mappings: 3 records ✅
- cids.discovered_permissions: 0 records ⚠️
```

## Next Steps
1. Decision needed on how to handle orphaned data
2. Re-run migration after fix
3. Verify all data migrated correctly
4. Update backend to use Supabase instead of JSON files

## Notes
- The `is_active` field question needs verification after roles are successfully migrated
- Consider adding data validation step before migration
- May need to implement better error handling in migration script