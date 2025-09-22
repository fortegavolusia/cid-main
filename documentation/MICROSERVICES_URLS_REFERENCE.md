# Microservices URLs Reference
**Fecha:** 19 de Septiembre de 2025
**Sistema:** CID + Bank System + HR System + Inventory System

## Resumen

Este documento contiene las URLs de todos los microservicios del ecosistema CIDS para referencia de desarrollo y configuración.

## Bank System
**Puerto:** 8006
**Contenedor:** `bank-system`

### URLs Docker (Para comunicación entre servicios)
- **Discovery:** `http://bank-system:8006/discovery/endpoints`
- **Health:** `http://bank-system:8006/health`
- **Metadata:** `http://bank-system:8006/discovery/metadata`
- **Refresh Discovery:** `http://bank-system:8006/discovery/refresh`

### URLs Localhost (Para acceso directo)
- **Discovery:** `http://localhost:8006/discovery/endpoints`
- **Health:** `http://localhost:8006/health`
- **Metadata:** `http://localhost:8006/discovery/metadata`

### Configuración CIDS
- **Client ID:** `app_aba3d3708aed4926`
- **API Key:** `cids_ak_ICXdGZrRkqKTMG3TLUHDEzYUhpWRhdDS`

### Endpoints Principales
- **Account Balance:** `GET /accounts/{employee_id}/balance`
- **Account Details:** `GET /accounts/{employee_id}/details`
- **Transactions:** `GET /transactions/{employee_id}`
- **Process Payroll:** `POST /payroll/process`
- **Batch Payroll:** `POST /payroll/batch`
- **Banking Info:** `GET /banking/{employee_id}`

### Configuración Actual
```
BASE_URL = http://localhost:8006  # ❌ PROBLEMA: Debe ser http://bank-system:8006
CIDS_BASE_URL = http://cid-backend:8000  # ✅ CORRECTO
```

---

## HR System
**Puerto:** 8005
**Contenedor:** `hr-system`

### URLs Docker (Para comunicación entre servicios)
- **Discovery:** `http://hr-system:8005/discovery/endpoints`
- **Dashboard:** `http://hr-system:8005/dashboard`
- **SSO:** `http://hr-system:8005/auth/sso`
- **Health:** `http://hr-system:8005/health`

### URLs Localhost (Para acceso directo)
- **Discovery:** `http://localhost:8005/discovery/endpoints`
- **Dashboard:** `http://localhost:8005/dashboard`
- **SSO:** `http://localhost:8005/auth/sso`
- **Health:** `http://localhost:8005/health`
- **Login:** `http://localhost:8005/login`
- **Root:** `http://localhost:8005/`

### Configuración CIDS
- **App ID:** `app_fba7654e91e6413c`
- **Client ID:** Configurado via variables de entorno
- **API Key:** Configurado via variables de entorno

### Endpoints Principales
- **List Employees:** `GET /api/employees`
- **Search Employees:** `GET /api/employees/search`
- **Get Employee:** `GET /api/employees/{employee_id}`
- **List Payments:** `GET /api/payments`
- **Bank Balance (A2A):** `GET /api/bank-balance`

### Configuración Actual
```
BASE_URL = http://localhost:8005  # ❌ PROBLEMA: Debe ser http://hr-system:8005
CIDS_BASE_URL = http://cid-backend:8000  # ✅ CORRECTO
```

---

## Inventory System
**Ubicación:** `/home/dpi/projects/inventory`
**Puerto Backend:** 8003
**Puerto Frontend:** 3001
**Contenedores:** `inventory-backend`, `inventory-frontend`

### URLs Docker (Para comunicación entre servicios)
- **Discovery:** `http://inventory-backend:8003/discovery/endpoints`
- **Backend Dashboard:** `http://inventory-backend:8003/dashboard.html`
- **Backend Health:** `http://inventory-backend:8003/health`
- **Backend SSO:** `http://inventory-backend:8003/auth/sso`
- **Frontend:** `http://inventory-frontend:3001`
- **Frontend Health:** `http://inventory-frontend:3001/api/health`

### URLs Localhost (Para acceso directo)
- **Discovery:** `http://localhost:8003/discovery/endpoints`
- **Backend Dashboard:** `http://localhost:8003/dashboard.html`
- **Backend Health:** `http://localhost:8003/health`
- **Backend SSO:** `http://localhost:8003/auth/sso`
- **Frontend App:** `http://localhost:3001`
- **Frontend Health:** `http://localhost:3001/api/health`

### Endpoints API Backend
- **Items:** `GET /api/items`
- **Categories:** `GET /api/categories`
- **Locations:** `GET /api/locations`
- **My Inventory:** `GET /api/my-inventory`
- **Stats:** `GET /api/stats`

### Configuración CIDS
- **Client ID:** `app_435bdc37ae0d494f`
- **API Key:** `cids_ak_2mePJeXPpOhvGIkjqok80ijwUPpM6S0D`
- **CIDS Base URL:** `http://cid-backend:8000`

### Configuración Frontend
- **Next.js App:** Puerto 3001
- **API URL:** `http://localhost:8003` (para desarrollo)
- **CIDS URL:** `http://localhost:8001` (para desarrollo)

### Configuración Actual
```
# Backend
CIDS_BASE_URL = http://cid-backend:8000  # ✅ CORRECTO
CIDS_CLIENT_ID = app_435bdc37ae0d494f    # ✅ ACTUALIZADO

# Frontend
NEXT_PUBLIC_API_URL = http://localhost:8003     # ⚠️ Para desarrollo
NEXT_PUBLIC_CIDS_URL = http://localhost:8001    # ⚠️ Para desarrollo
```

---

## CID System
**Puerto Frontend:** 3000 (HTTPS)
**Puerto Backend:** 8001
**Contenedores:** `cid-frontend`, `cid-backend`

### URLs Frontend (HTTPS requerido para Azure AD)
- **Dashboard:** `https://localhost:3000`
- **Admin:** `https://localhost:3000/admin`
- **Token Administration:** `https://localhost:3000/token-administration`
- **Login:** `https://localhost:3000/login`

### URLs Backend
- **Health:** `http://localhost:8001/auth/health`
- **Token Exchange:** `POST http://localhost:8001/auth/token/exchange`
- **Validate:** `GET http://localhost:8001/auth/validate`
- **JWKS:** `GET http://localhost:8001/.well-known/jwks.json`
- **Discovery:** `POST http://localhost:8001/discovery/endpoints/{client_id}`

### URLs Docker (Backend)
- **Health:** `http://cid-backend:8000/auth/health`
- **Token Exchange:** `POST http://cid-backend:8000/auth/token/exchange`
- **Validate:** `GET http://cid-backend:8000/auth/validate`

---

## Problemas Identificados

### 1. BASE_URL Incorrecto en Microservicios
**Bank System:** Usa `http://localhost:8006` pero debería usar `http://bank-system:8006`
**HR System:** Usa `http://localhost:8005` pero debería usar `http://hr-system:8005`

### 2. Impacto en Discovery
Cuando CIDS intenta hacer discovery de estos servicios, no puede acceder porque los endpoints reportan URLs localhost en lugar de nombres de servicios Docker.

### 3. Solución Recomendada
Actualizar las variables de entorno en docker-compose.yml:

**Bank System:**
```yaml
environment:
  - BASE_URL=http://bank-system:8006  # Cambiar de localhost
```

**HR System:**
```yaml
environment:
  - BASE_URL=http://hr-system:8005   # Cambiar de localhost
```

---

## Redes Docker

### Redes Compartidas
- **cid_cid-network:** Compartida entre CID, Bank, HR e Inventory
- **supabase_network_mi-proyecto-supabase:** Base de datos compartida

### Comunicación Entre Servicios
- CID → Bank System: `http://bank-system:8006`
- CID → HR System: `http://hr-system:8005`
- CID → Inventory: `http://inventory-backend:8003`
- HR → Bank (A2A): `http://bank-system:8006`

---

## Notas de Desarrollo

1. **Discovery URLs:** Siempre usar nombres de servicios Docker para que CIDS pueda acceder
2. **Frontend URLs:** Pueden usar localhost porque se acceden desde navegador
3. **Backend-to-Backend:** Siempre usar nombres de servicios Docker
4. **Health Checks:** Usar localhost dentro del contenedor, nombres de servicios desde fuera

---

*Generado el 19 de Septiembre de 2025*
*Verificado con configuraciones actuales de docker-compose.yml*