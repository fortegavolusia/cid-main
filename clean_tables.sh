#!/bin/bash

# Script to clean ALL CID and UUID Service database tables (except photo_emp)
# CID Tables: rls_filters, role_permissions, role_metadata, permissions, field_metadata,
# discovery_history, discovery_endpoints, discovered_permissions, app_role_mappings,
# activity_log, api_keys, token_activity, revoked_tokens, refresh_tokens,
# a2a_permissions, registered_apps, rotation_policies, token_templates
# UUID Service Tables: generated_ids, generation_log

echo "============================================"
echo "CID Database Tables Cleanup Script"
echo "============================================"
echo ""

# Database connection parameters
DB_HOST="localhost"
DB_PORT="54322"
DB_NAME="postgres"
DB_USER="postgres"
DB_PASS="postgres"

echo "Connecting to database at $DB_HOST:$DB_PORT..."
echo ""

# Function to execute SQL using docker
execute_sql() {
    docker exec -e PGPASSWORD=$DB_PASS supabase_db_mi-proyecto-supabase psql -h localhost -U $DB_USER -d $DB_NAME -c "$1" 2>&1
}

# First attempt - try to delete all tables
echo "First cleanup attempt - trying to delete from all tables..."
echo "-----------------------------------------------------------"

tables=(
    "cids.rls_filters"
    "cids.role_permissions"
    "cids.role_metadata"
    "cids.permissions"
    "cids.field_metadata"
    "cids.discovery_history"
    "cids.discovery_endpoints"
    "cids.discovered_permissions"
    "cids.app_role_mappings"
    "cids.activity_log"
    "cids.api_keys"
    "cids.token_activity"
    "cids.revoked_tokens"
    "cids.refresh_tokens"
    "cids.a2a_permissions"
    "cids.registered_apps"
    "cids.rotation_policies"
    "cids.token_templates"
    "uuid_service.generated_ids"
    "uuid_service.generation_log"
)

for table in "${tables[@]}"; do
    echo "Cleaning table: $table"
    result=$(execute_sql "DELETE FROM $table;")
    if echo "$result" | grep -q "ERROR"; then
        echo "  ⚠ Warning: Could not clean $table (might have constraints)"
    else
        count=$(echo "$result" | grep -oE 'DELETE [0-9]+' | grep -oE '[0-9]+')
        if [ -z "$count" ]; then
            count="0"
        fi
        echo "  ✓ Deleted $count rows from $table"
    fi
done

echo ""
echo "Second cleanup attempt - retrying failed tables..."
echo "---------------------------------------------------"

# Second attempt - retry any failed tables
for table in "${tables[@]}"; do
    result=$(execute_sql "SELECT COUNT(*) FROM $table;")
    count=$(echo "$result" | grep -oE '^\s*[0-9]+' | tail -1 | tr -d ' ')
    
    if [ "$count" != "0" ] && [ ! -z "$count" ]; then
        echo "Retrying table: $table (still has $count rows)"
        result=$(execute_sql "DELETE FROM $table;")
        if echo "$result" | grep -q "ERROR"; then
            echo "  ✗ Error: Still could not clean $table"
        else
            deleted=$(echo "$result" | grep -oE 'DELETE [0-9]+' | grep -oE '[0-9]+')
            if [ -z "$deleted" ]; then
                deleted="0"
            fi
            echo "  ✓ Deleted $deleted rows from $table"
        fi
    fi
done

echo ""
echo "Final status check..."
echo "---------------------"

# Show final row counts
for table in "${tables[@]}"; do
    result=$(execute_sql "SELECT COUNT(*) FROM $table;")
    # Extract just the number from the result
    count=$(echo "$result" | awk '/^\s*[0-9]+$/ {print $1}' | head -1)
    
    if [ -z "$count" ]; then
        echo "? $table: Unable to check"
    elif [ "$count" = "0" ]; then
        echo "✓ $table: CLEAN (0 rows)"
    else
        echo "✗ $table: Still has $count rows"
    fi
done

echo ""
echo "============================================"
echo "CLEANUP SUMMARY"
echo "============================================"

# Track totals
total_cleaned=0
total_failed=0
cleaned_tables=""
failed_tables=""

# Generate summary
for table in "${tables[@]}"; do
    result=$(execute_sql "SELECT COUNT(*) FROM $table;")
    count=$(echo "$result" | awk '/^\s*[0-9]+$/ {print $1}' | head -1)

    if [ -z "$count" ]; then
        failed_tables="$failed_tables\n  - $table: Unable to check"
        total_failed=$((total_failed + 1))
    elif [ "$count" = "0" ]; then
        cleaned_tables="$cleaned_tables\n  - $table: Successfully cleaned"
        total_cleaned=$((total_cleaned + 1))
    else
        failed_tables="$failed_tables\n  - $table: Still has $count rows"
        total_failed=$((total_failed + 1))
    fi
done

echo ""
echo "Tables cleaned successfully: $total_cleaned/${#tables[@]}"
if [ ! -z "$cleaned_tables" ]; then
    echo -e "$cleaned_tables"
fi

if [ $total_failed -gt 0 ]; then
    echo ""
    echo "Tables with issues: $total_failed"
    echo -e "$failed_tables"
fi

echo ""
echo "============================================"
echo "Cleanup complete!"
echo "============================================"