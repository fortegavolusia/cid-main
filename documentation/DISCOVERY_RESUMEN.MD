# DISCOVERY - RESUMEN DEL PROCESO

## Proceso Actual de Discovery (4 Pasos)

### PASO 1 (Inicio del Proceso)
- **Genera ID único**: Solicita a UUID service un ID con prefijo `dis_` 
- **Registra actividad**: Inserta registro en `activity_log` con estado "started"
- **Datos guardados**: activity_id, activity_type, entity_type, entity_id, user_email, status

### PASO 2 (Discovery y Versionado)
- **Ejecuta discovery**: Llama al endpoint de discovery del app registrado
- **Manejo de versiones**: Incrementa automáticamente la versión del discovery
- **Guarda historial**: Inserta en `discovery_history` con:
  - discovery_id (el mismo `dis_` del paso 1)
  - client_id
  - discovery_version (incremental)
  - endpoints_count
  - discovery_data (respuesta completa)
  - discovered_by (email del usuario)

### PASO 3 (Almacenamiento de Endpoints)
- **Procesa endpoints**: Itera sobre cada endpoint descubierto
- **Genera IDs únicos**: Solicita a UUID service un `end_` ID para cada endpoint
- **Guarda en BD**: Inserta en `discovery_endpoints` con:
  - endpoint_id (único con prefijo `end_`)
  - discovery_id (el mismo `dis_` del proceso)
  - method (GET, POST, PUT, DELETE, etc.)
  - path (ruta del endpoint)
  - resource (entidad principal)
  - action (operación: read, write, delete)
  - parameters (parámetros del endpoint)
  - response_fields (campos de respuesta)

### PASO 4 (Generación de Permisos)
- **Agrupa permisos**: Combina permisos únicos por resource + action
- **Genera IDs únicos**: Solicita a UUID service un `per_` ID para cada permiso
- **Guarda en BD**: Inserta en `discovered_permissions` con:
  - permission_id (único con prefijo `per_`)
  - discovery_id (el mismo `dis_` del proceso)
  - client_id
  - resource
  - action
  - available_fields (campos disponibles agregados)
  - is_active (true por defecto)
- **Actualiza estado**: Cambia activity_log a "completed"

## Tablas de Base de Datos Involucradas

1. **activity_log**: Registro de auditoría de todas las actividades
2. **discovery_history**: Historial de todos los discoveries con versionado
3. **discovery_endpoints**: Detalle de cada endpoint descubierto
4. **discovered_permissions**: Permisos generados del discovery

## Prefijos de IDs Utilizados

- `dis_`: Discovery ID (uno por proceso completo)
- `end_`: Endpoint ID (uno por cada endpoint)
- `per_`: Permission ID (uno por cada permiso único)

## Posibles Mejoras Futuras

### 1. Validación de Cambios
- Comparar con discovery anterior
- Detectar endpoints nuevos, modificados o eliminados
- Generar reporte de diferencias

### 2. Notificaciones
- Alertar administradores sobre cambios importantes
- Enviar email si se detectan endpoints críticos modificados
- Notificar si se pierden permisos existentes

### 3. Sincronización de Roles
- Actualizar automáticamente roles afectados por cambios
- Reasignar permisos cuando cambian los endpoints
- Mantener coherencia entre permisos y roles

### 4. Generación de Documentación
- Crear documentación API automática (OpenAPI/Swagger)
- Generar ejemplos de uso para cada endpoint
- Mantener changelog de cambios entre versiones

### 5. Testing Automático
- Validar que los endpoints respondan correctamente
- Verificar autenticación y autorización
- Probar con datos de ejemplo

### 6. Métricas y Estadísticas
- Guardar estadísticas de uso por endpoint
- Tracking de performance por endpoint
- Análisis de endpoints más/menos utilizados
- Tendencias de uso en el tiempo

## Configuración Actual

- **Backend API**: Puerto 8001
- **UUID Service**: Puerto 8002 (container: uuid-service-dev)
- **PostgreSQL**: Puerto 54322 (host) / 5432 (container: supabase_db_mi-proyecto-supabase)
- **Schema BD**: cids

## Notas Importantes

- El discovery mantiene un historial completo de auditoría
- Cada ejecución genera nuevos registros (no sobrescribe)
- Los IDs con prefijos permiten trazabilidad completa
- El versionado es automático e incremental por client_id