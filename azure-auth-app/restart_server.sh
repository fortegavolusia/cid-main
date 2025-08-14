#!/bin/bash
# Script to safely restart the auth service

echo "Restarting main.py..."

# Find and kill the existing process
OLD_PID=$(ps aux | grep -E "[p]ython.*main.py|[u]vicorn.*main:app|[u]vicorn.*auth_service:app" | awk '{print $2}')
if [ ! -z "$OLD_PID" ]; then
    echo "Stopping existing server (PID: $OLD_PID)..."
    kill $OLD_PID
    sleep 2
else
    echo "No existing server process found."
fi

# Start the server in the background using uvicorn
echo "Starting new server..."
cd /home/jnbailey/Desktop/CIDS/azure-auth-app
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload > server.log 2>&1 &
NEW_PID=$!

echo "Server started with PID: $NEW_PID"
echo "Logs are being written to server.log"
echo ""
echo "Wait a few seconds for the server to start, then:"
echo "1. Login again at https://localhost:8000/auth/login"
echo "2. Check your token at https://localhost:8000/auth/my-token"
echo "3. View all tokens at https://localhost:8000/auth/admin/tokens (requires admin access)"
echo ""
echo "To view logs: tail -f server.log"