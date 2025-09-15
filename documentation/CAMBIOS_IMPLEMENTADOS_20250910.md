# Cambios Implementados - 10 de Septiembre 2025

## 🔧 TODOS LOS CAMBIOS ESTÁN EN LOS ARCHIVOS DEL PROYECTO

### 1. **Manejo de Conexiones a Base de Datos**
**Archivo:** `/backend/services/database.py`
- **Líneas 53, 59:** Agregado `self.disconnect()` en `execute_query()`
- **Líneas 72, 80:** Agregado `self.disconnect()` en `execute_update()`
- **Propósito:** Cerrar conexiones después de cada operación para evitar fugas de conexiones a Supabase

### 2. **Foreign Key para rol_id en app_role_mappings**
**Script SQL:** `/add_role_id_fk.sql`
```sql
ALTER TABLE cids.app_role_mappings 
ADD CONSTRAINT app_role_mappings_rol_id_fkey 
FOREIGN KEY (rol_id) 
REFERENCES cids.role_metadata(role_id) 
ON DELETE CASCADE;
```

**Archivo:** `/backend/services/app_registration.py`
- **Líneas 254-287:** Obtener o crear `role_id` y usar UUID service
- **Línea 294:** INSERT incluye `rol_id` en app_role_mappings

### 3. **Activity Log para role.create**
**Archivo:** `/backend/api/main.py`
- **Línea 2053:** Cambiado a `action="role.create"`
- **Líneas 2054-2062:** Incluye user_email, user_id, client_id, role_name

**Archivo:** `/backend/services/permission_registry.py`
- **Líneas 305-310:** Verifica si el rol tiene permisos existentes
- **Línea 311:** Determina si es `role.create` o `role.update`
- **Líneas 325-339:** Log con el tipo correcto de actividad

### 4. **Logout en Activity Log**
**Archivo:** `/backend/api/main.py`
- **Líneas 761-799:** Nuevo endpoint `POST /auth/logout`
- **Líneas 785-794:** Usa `db_service.log_activity()` como login
- **Acción:** "logout" con email y timestamp

**Archivo:** `/cids-frontend/src/services/authService.ts`
- **Línea 140:** Cambiado a `apiService.post('/auth/logout', {})`

**Archivo:** `/cids-frontend/src/services/api.ts`
- **Líneas 24-26:** Removido `/auth/logout` de exclusiones del token

### 5. **Roles Modal siempre lee de BD**
**Archivo:** `/cids-frontend/src/components/RolesModal.tsx`
- **Línea 6:** Agregado `import apiService from '../services/api';`
- **Línea 474:** Llama con `use_cache=false` para forzar lectura de BD
- **Línea 295:** Removido título duplicado "Create New Role"

### 6. **Cache Refresh Button**
**Archivo:** `/backend/api/main.py`
- **Líneas 2040-2048:** Endpoint `POST /auth/admin/refresh-cache`
- **Línea 2044:** Llama `permission_registry._load_registry()`

**Archivo:** `/cids-frontend/src/services/adminService.ts`
- **Líneas 238-240:** Método `refreshCache()`

**Archivo:** `/cids-frontend/src/pages/AdminPageNew.tsx`
- **Líneas 378-389:** Función `handleRefreshCache`
- **Líneas 553-556:** Botón "Refresh Cache" en Quick Actions

### 7. **Fix para Error 500 en Creación de Roles**
**Archivo:** `/backend/services/permission_registry.py`
- **Líneas 276-286:** Lee permisos como JSONB en lugar de columnas individuales
- **Línea 287:** Parsea JSON correctamente para obtener permisos

## 📦 Docker Compose Configuration
**Archivo:** `/docker-compose.yml`
- **Línea 42:** Volumen `./backend:/app` activo para desarrollo
- **Línea 63:** VITE_API_ORIGIN configurado correctamente

## 🗃️ Base de Datos
- Tabla `cids.app_role_mappings` tiene campo `rol_id` con foreign key
- Tabla `cids.activity_log` registra login/logout
- Tabla `cids.role_metadata` almacena metadatos de roles
- Tabla `cids.role_permissions` usa JSONB para permisos

## ✅ Estado Actual
- Todos los cambios están persistidos en los archivos del proyecto
- El rebuild de Docker incluirá todos estos cambios
- Las conexiones a BD se cierran automáticamente
- Activity Log registra correctamente role.create y logout
- Cache se puede refrescar sin reiniciar servidor
- Roles Modal no muestra título duplicado
- Error 500 al crear roles está resuelto

## 🔍 Problema de Logs Duplicados
**Estado:** EN PROGRESO
- Al crear un rol se generan dos entradas en Activity Log
- Una dice role.update y otra role.create
- Fix aplicado en `permission_registry.py` para detectar si es creación o actualización

## 🚀 Para Rebuild Completo
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---
**Última actualización:** 10 de Septiembre 2025, 5:00 PM
**Verificado:** Todos los cambios están en los archivos del proyecto