# Documentación del Flujo de Discovery - CID

## ¿Qué es Discovery?

Discovery es un mecanismo automático que permite a CID (Centralized Identity Discovery) descubrir y catalogar automáticamente todos los endpoints, recursos y permisos de las aplicaciones registradas. Es como un "escaneo inteligente" que documenta qué puede hacer cada aplicación.

## Propósito Principal

1. **Automatización**: Elimina la necesidad de configurar manualmente los permisos
2. **Sincronización**: Mantiene CID actualizado con los cambios en las aplicaciones
3. **Seguridad**: Detecta automáticamente campos sensibles (PII, PHI, datos financieros)
4. **Control Granular**: Permite control a nivel de campo para cada recurso

## Flujo Completo del Discovery

### 1. Iniciación del Discovery
```
Usuario/Admin → CID Frontend → POST /discovery/endpoints/{client_id}
```
- Se puede ejecutar manualmente desde la UI
- Se puede forzar con parámetro `force=true`
- Requiere autenticación de administrador

### 2. Validación Inicial
CID verifica:
- ✅ La aplicación existe en la base de datos
- ✅ La aplicación permite discovery (`allow_discovery = true`)
- ✅ Existe un endpoint de discovery configurado
- ✅ El endpoint está accesible (health check opcional)

### 3. Solicitud al Endpoint de Discovery
```
CID Backend → GET http://app-name:port/discovery/endpoints
```
CID envía:
- Token JWT de servicio para autenticación
- Headers con información del solicitante

### 4. Respuesta de la Aplicación
La aplicación responde con estructura v2.0:
```json
{
  "version": "2.0",
  "app_id": "app_fba7654e91e6413c",  // DEBE coincidir con client_id en CID
  "app_name": "HR System",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/employees",
      "resource": "employees",
      "action": "read",
      "response_fields": {
        "id": {"type": "string"},
        "salary": {
          "type": "number",
          "sensitivity": {
            "is_financial": true,
            "is_sensitive": true
          }
        },
        "ssn": {
          "type": "string", 
          "sensitivity": {
            "is_pii": true,
            "is_sensitive": true
          }
        }
      }
    }
  ]
}
```

### 5. Procesamiento de la Respuesta

#### 5.1 Validación de Estructura
- Verifica formato v2.0
- Valida que `app_id` coincida con `client_id`
- Comprueba campos requeridos

#### 5.2 Generación de Permisos
Para cada endpoint descubierto:
```
Recurso: employees
Acción: read
Campos disponibles: [id, name, salary, ssn, ...]
Sensibilidad: salary=financial, ssn=PII
```

#### 5.3 Clasificación de Sensibilidad
Automáticamente detecta y marca:
- **PII** (Personally Identifiable Information): SSN, dirección, teléfono
- **PHI** (Protected Health Information): información médica
- **Financial**: salarios, cuentas bancarias, montos
- **Sensitive**: cualquier dato considerado sensible

### 6. Almacenamiento de Datos

#### 6.1 Base de Datos (Prioridad)
Los datos se guardan en el esquema CIDS de Supabase:

**Tabla: discovery_history**
- Historial completo de cada ejecución
- Timestamp, versión, cantidad de endpoints
- Estado (success/failed)

**Tabla: discovery_endpoints**
- Detalle de cada endpoint descubierto
- Método HTTP, path, recurso, acción
- Parámetros y campos de respuesta

**Tabla: discovered_permissions**
- Permisos generados por recurso/acción
- Lista de campos disponibles
- Marcadores de sensibilidad por campo

**Tabla: activity_log**
- Registro de auditoría
- Quién ejecutó discovery y cuándo

#### 6.2 Archivos JSON (Backup/Legacy)
Actualmente también guarda en:
- `discovered_permissions.json`
- `discovery_history.json`
- `app_endpoints.json`

### 7. Actualización del Estado
- Actualiza `last_discovery_at` en la app
- Cambia `discovery_status` a "success" o "error"
- Incrementa contador de ejecuciones

### 8. Cache y Optimización
- Los resultados se cachean por 5 minutos (configurable)
- Si no se fuerza, usa cache si está disponible
- Evita llamadas innecesarias a las aplicaciones

## Casos de Error

### Errores Comunes
1. **App ID Mismatch**: El `app_id` en la respuesta no coincide con `client_id`
2. **Endpoint No Accesible**: La aplicación está caída o no responde
3. **Formato Incorrecto**: No cumple con especificación v2.0
4. **Sin Permisos**: Token no válido o sin autorización

### Manejo de Errores
- Clasifica el tipo de error
- Registra en activity_log
- Actualiza discovery_status con el tipo de error
- Mantiene datos anteriores si existen

## Beneficios del Sistema

### Para Administradores
- No necesitan conocer todos los endpoints de cada aplicación
- Actualizaciones automáticas cuando cambia una API
- Vista centralizada de todos los permisos
- Control granular sobre campos sensibles

### Para Desarrolladores
- Solo implementan endpoint `/discovery/endpoints`
- No coordinación manual con equipo de seguridad
- Cambios en API se reflejan automáticamente
- Estándar claro y documentado

### Para Seguridad
- Visibilidad completa de datos sensibles
- Auditoría automática de accesos
- Políticas RLS basadas en campos descubiertos
- Compliance automático (GDPR, HIPAA, etc.)

## Flujo Visual Simplificado

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Admin     │────>│     CID     │────>│     App     │
│   Clicks    │     │   Backend   │     │   (HR)      │
│  Discovery  │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           │   GET /discovery   │
                           │────────────────────>
                           │                    │
                           │   JSON Response    │
                           │<────────────────────
                           │                    │
                    ┌──────▼──────┐             │
                    │  Process &  │             │
                    │  Generate   │             │
                    │ Permissions │             │
                    └──────┬──────┘             │
                           │                    │
                    ┌──────▼──────┐             │
                    │   Save to   │             │
                    │   Supabase  │             │
                    │   Database  │             │
                    └─────────────┘             │
```

## Estado Actual del Problema

### ✅ Funcionando
- Discovery ejecuta correctamente
- Encuentra los 9 endpoints de HR System
- Genera 45 permisos
- Guarda en discovery_history
- Guarda en discovery_endpoints

### ❌ Problemas Identificados
1. **discovered_permissions vacía**: Los permisos no se están guardando
2. **Doble escritura**: Escribe en JSON Y en base de datos
3. **Prioridad incorrecta**: JSON tiene prioridad sobre base de datos

### 🔧 Solución en Progreso
1. Hacer que la base de datos sea la fuente principal
2. JSON solo como backup opcional
3. Corregir el guardado de discovered_permissions
4. Eliminar dependencias de archivos JSON

---

*Documento creado para entender el flujo completo del Discovery en CID*
*Última actualización: Enero 2025*