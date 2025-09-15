#!/bin/bash

# Script para iniciar CID Backend con configuración correcta de base de datos

echo "🚀 Iniciando CID Backend con configuración estable..."

# Configuración de base de datos para contenedores Docker
export DB_HOST=supabase_db_mi-proyecto-supabase
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=postgres

# Cargar variables de Azure desde .env si existe
if [ -f .env ]; then
    export $(cat .env | grep -E "^AZURE_|^ADMIN_" | xargs)
    echo "✅ Variables de Azure cargadas desde .env"
fi

# Detener y eliminar contenedor existente
docker stop cid-backend 2>/dev/null
docker rm cid-backend 2>/dev/null

# Iniciar contenedor con las variables correctas
docker run -d \
    --name cid-backend \
    --network supabase_network_mi-proyecto-supabase \
    --network uuid-service_uuid-network \
    -p 8001:8000 \
    -e DB_HOST=$DB_HOST \
    -e DB_PORT=$DB_PORT \
    -e DB_NAME=$DB_NAME \
    -e DB_USER=$DB_USER \
    -e DB_PASSWORD=$DB_PASSWORD \
    -e AZURE_TENANT_ID=$AZURE_TENANT_ID \
    -e AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    -e AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
    -e ADMIN_EMAILS="FOrtega@volusia.gov" \
    -e DEV_CROSS_ORIGIN=true \
    -e PERSIST_KEYS=true \
    -v $(pwd)/backend:/app \
    -v $(pwd)/backend/infra/data:/app/infra/data \
    cid-backend:latest \
    uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Conectar a la red adicional
docker network connect uuid-service_uuid-network cid-backend 2>/dev/null

echo "✅ CID Backend iniciado con configuración estable"
echo "📝 Configuración:"
echo "   - DB_HOST: $DB_HOST"
echo "   - DB_PORT: $DB_PORT"
echo "   - API: http://localhost:8001"

# Verificar conexión
sleep 3
echo ""
echo "🔍 Verificando conexión a base de datos..."
docker exec cid-backend python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    print('✅ Conexión a base de datos exitosa!')
    conn.close()
except Exception as e:
    print(f'❌ Error de conexión: {e}')
"

# Verificar health endpoint
echo ""
echo "🔍 Verificando API..."
sleep 2
curl -s http://localhost:8001/auth/health > /dev/null 2>&1 && echo "✅ API funcionando!" || echo "⏳ API iniciándose..."