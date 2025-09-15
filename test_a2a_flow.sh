#!/bin/bash

echo "=== Test A2A Flow: HR System → Bank System ==="
echo ""

# Step 1: HR requests service token from CIDS
echo "[1] HR System requesting service token from CIDS..."
RESPONSE=$(curl -s -X POST http://localhost:8001/auth/service-token \
  -H "X-API-Key: cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV" \
  -H "Content-Type: application/json" \
  -d '{
    "target_client_id": "app_aba3d3708aed4926",
    "requested_scopes": ["accounts.read", "accounts.balance"],
    "duration": 300,
    "purpose": "Test HR to Bank communication"
  }')

# Extract token from response
SERVICE_TOKEN=$(echo $RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
EXPIRES_IN=$(echo $RESPONSE | grep -o '"expires_in":[0-9]*' | cut -d':' -f2)

if [ -z "$SERVICE_TOKEN" ]; then
    echo "❌ Failed to get service token"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Service token obtained (expires in ${EXPIRES_IN}s)"
echo "Token (first 50 chars): ${SERVICE_TOKEN:0:50}..."
echo ""

# Step 2: HR uses token to call Bank API
echo "[2] HR System calling Bank API with service token..."
BANK_RESPONSE=$(curl -s -X GET http://localhost:8006/accounts/emp_001/balance \
  -H "Authorization: Bearer $SERVICE_TOKEN")

echo "Bank API Response:"
echo "$BANK_RESPONSE"
echo ""

# Step 3: Validate token at CIDS
echo "[3] Validating service token at CIDS..."
VALIDATION=$(curl -s -X POST http://localhost:8001/auth/validate \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$SERVICE_TOKEN\"}")

echo "Token validation result:"
echo "$VALIDATION"
echo ""

# Step 4: Check activity log
echo "[4] Checking CIDS activity log for A2A events..."
docker exec -i supabase_db_mi-proyecto-supabase psql -U postgres -d postgres << 'EOF'
SELECT
    activity_type,
    entity_type,
    entity_name,
    created_at
FROM cids.activity_log
WHERE activity_type LIKE '%a2a%'
ORDER BY created_at DESC
LIMIT 5;
EOF

echo ""
echo "=== A2A Flow Test Complete ==="