# County Services - Microservices Architecture

## 📁 Estructura de Directorios

```
/home/dpi/projects/
├── CID/                      # Core Identity Service (CIDS)
│   ├── backend/             # FastAPI backend
│   ├── cids-frontend/       # React frontend admin
│   └── Dockerfile
│
├── services-portal/          # Portal de Servicios (Microservicio)
│   ├── src/                 # React app source
│   ├── Dockerfile          
│   └── k8s/                 # Kubernetes manifests
│       └── deployment.yaml
│
├── uuid-service/             # Servicio UUID (Microservicio)
│   ├── src/                 # Python FastAPI source
│   ├── Dockerfile
│   ├── requirements.txt
│   └── k8s/                 # Kubernetes manifests
│       └── deployment.yaml
│
├── docker-compose.yml        # Orquestación local
├── deploy.sh                 # Script de deployment
└── k8s-namespace.yaml       # Namespace de Kubernetes
```

## 🐳 Desarrollo Local con Docker

### Iniciar todos los servicios:
```bash
cd /home/dpi/projects
docker-compose up -d
```

### Servicios disponibles:
- **CIDS Backend**: http://localhost:8001
- **CIDS Frontend**: https://localhost:3000
- **Services Portal**: http://localhost:4000
- **UUID Service**: http://localhost:8002
- **PostgreSQL**: localhost:54322

### Ver logs:
```bash
docker-compose logs -f [service-name]
```

### Detener servicios:
```bash
docker-compose down
```

## ☸️ Deployment a Kubernetes

### 1. Construir imágenes Docker:
```bash
./deploy.sh
```

### 2. Push a registry y deploy:
```bash
PUSH_TO_REGISTRY=true DEPLOY_TO_K8S=true ./deploy.sh
```

### 3. Verificar deployment:
```bash
kubectl get pods -n county-services
kubectl get services -n county-services
kubectl get ingress -n county-services
```

## 🏗️ Arquitectura de Microservicios

### Services Portal
- **Propósito**: Portal de empleados del condado
- **Stack**: React + Vite + TypeScript
- **Features**: 
  - Decodifica JWT de CIDS
  - Dashboard con permisos y roles
  - Acceso a aplicaciones autorizadas
- **Kubernetes**: 3 réplicas, Ingress en portal.county.gov

### UUID Service
- **Propósito**: Generación centralizada de IDs únicos
- **Stack**: FastAPI + PostgreSQL
- **Features**:
  - Genera UUIDs, ULIDs, NanoIDs
  - Tracking de IDs generados
  - API REST con estadísticas
- **Kubernetes**: 2-10 réplicas con HPA

### CIDS (Core Service)
- **Propósito**: Autenticación y autorización central
- **Stack**: FastAPI + PostgreSQL (Supabase)
- **Features**:
  - JWT issuing y validación
  - Integración con Azure AD
  - Gestión de roles y permisos
  - Row Level Security (RLS)

## 🔧 Configuración de Ambiente

### Variables de entorno necesarias:
```bash
# Para CIDS
AZURE_TENANT_ID=xxx
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx

# Para UUID Service
UUID_DB_HOST=postgres
UUID_DB_PORT=5432
UUID_DB_NAME=postgres
UUID_DB_USER=postgres
UUID_DB_PASSWORD=postgres
```

## 📊 Monitoreo

### Health checks:
- Services Portal: `GET /health`
- UUID Service: `GET /`
- CIDS Backend: `GET /auth/health`

### Métricas en Kubernetes:
```bash
kubectl top pods -n county-services
kubectl describe hpa -n county-services
```

## 🚀 CI/CD Pipeline (Sugerido)

1. **Build**: GitHub Actions construye imágenes
2. **Test**: Ejecuta tests unitarios y de integración
3. **Push**: Sube imágenes a registry privado
4. **Deploy**: ArgoCD o Flux sincroniza con cluster
5. **Monitor**: Prometheus + Grafana para métricas

## 🔐 Seguridad

- Todos los secrets en Kubernetes Secrets
- TLS habilitado en Ingress con cert-manager
- Network policies para aislar pods
- RBAC para acceso a recursos
- Scanning de imágenes con Trivy

## 📝 Notas Importantes

1. **Separación de servicios**: Cada microservicio es independiente y puede ser desplegado por separado
2. **Estado**: Solo PostgreSQL mantiene estado persistente
3. **Escalamiento**: Cada servicio escala independientemente según demanda
4. **Comunicación**: Los servicios se comunican via HTTP/REST
5. **Desarrollo**: docker-compose para desarrollo local, K8s para producción