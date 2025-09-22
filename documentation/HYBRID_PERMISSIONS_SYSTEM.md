# Sistema Híbrido de Permisos - CID

## Resumen Ejecutivo

Se ha implementado un modelo híbrido de permisos que combina tres niveles de granularidad para proporcionar control de acceso seguro y flexible, especialmente diseñado para entornos gubernamentales que requieren alta seguridad.

## Cambios Críticos Realizados

### 1. Corrección de Almacenamiento de Roles y Permisos

**Problema Original:**
- Las descripciones de roles no se guardaban
- Los permisos no se escribían en las tablas de base de datos
- Conflicto al intentar crear roles que ya existían

**Solución Implementada:**
- Separación clara entre creación de roles y actualización de permisos
- Flujo correcto: 
  1. Crear rol en `role_metadata`
  2. Si tiene grupo AD asignado, crear mapeo en `app_role_mappings`
  3. Guardar permisos tanto en `role_permissions` (JSON) como en `permissions` (registros individuales)

### 2. Modelo Híbrido de Permisos

**Arquitectura de Tres Niveles:**

#### Nivel 1: Permisos Base
- Formato: `resource.action`
- Ejemplo: `employees.read`
- Acceso: Solo campos no sensibles

#### Nivel 2: Permisos por Categoría
- Formato: `resource.action.category`
- Categorías soportadas:
  - **pii**: Información Personal Identificable (SSN, dirección, teléfono)
  - **sensitive**: Datos sensibles generales
  - **financial**: Información financiera (salario, bonos)
  - **phi**: Información de salud protegida
- Ejemplo: `employees.read.pii`, `employees.write.financial`

#### Nivel 3: Permisos por Campo Específico
- Formato: `resource.action.fieldname`
- Ejemplo: `employees.read.salary`, `employees.write.ssn`
- Control granular campo por campo

### 3. Compatibilidad Frontend-Backend

**Conversión Automática de Formatos:**
- Frontend envía: `resource:action:field`
- Backend convierte a: `resource.action.field`
- Validación inteligente que acepta permisos granulares si existe el permiso base

### 4. Dashboard Mejorado

**Nueva Funcionalidad:**
- Card "CID Database Info" ahora muestra conteo de permisos por rol
- Vista en tiempo real de la distribución de permisos
- Actualización automática al modificar roles

## Tablas de Base de Datos Utilizadas

### Tablas Principales

```sql
-- 1. role_metadata: Metadatos de roles
CREATE TABLE cids.role_metadata (
    role_id VARCHAR(50) PRIMARY KEY,  -- Formato: rol_xxxx
    client_id VARCHAR(100),
    role_name VARCHAR(100),
    description TEXT,
    a2a_only BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 2. role_permissions: Permisos JSON por rol
CREATE TABLE cids.role_permissions (
    per_id VARCHAR(50) PRIMARY KEY,  -- Formato: PER_xxxx
    client_id VARCHAR(100),
    role_name VARCHAR(100),
    permissions JSONB,  -- Array de permisos
    rls_filters JSONB,  -- Filtros RLS
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 3. permissions: Permisos individuales
CREATE TABLE cids.permissions (
    permission_id SERIAL PRIMARY KEY,
    role_id VARCHAR(50),  -- FK a role_metadata.role_id
    resource VARCHAR(100),
    action VARCHAR(50),
    fields JSONB,  -- Campos específicos
    resource_filters JSONB,  -- Filtros RLS
    per_id VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 4. field_metadata: Clasificación de campos
CREATE TABLE cids.field_metadata (
    field_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(100),
    resource VARCHAR(100),
    field_name VARCHAR(100),
    field_path VARCHAR(255),
    is_sensitive BOOLEAN DEFAULT false,
    is_pii BOOLEAN DEFAULT false,
    is_phi BOOLEAN DEFAULT false,
    is_financial BOOLEAN DEFAULT false,
    created_at TIMESTAMP
);

-- 5. discovered_permissions: Permisos disponibles
CREATE TABLE cids.discovered_permissions (
    permission_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(100),
    resource VARCHAR(100),
    action VARCHAR(50),
    category VARCHAR(50) DEFAULT 'base',  -- Nueva columna
    description TEXT,
    discovered_at TIMESTAMP,
    last_validated TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 6. app_role_mappings: Mapeo AD grupos a roles
CREATE TABLE cids.app_role_mappings (
    mapping_uuid VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(100),
    ad_group_name VARCHAR(255),
    role_name VARCHAR(100),
    rol_id VARCHAR(50),  -- FK a role_metadata.role_id
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Flujo de Validación de Permisos

### 1. Recepción de Permisos desde Frontend
```python
# Frontend envía formato con dos puntos
permission = "employees:read:department"

# Backend convierte automáticamente
if ':' in permission:
    parts = permission.split(':')
    permission = f"{parts[0]}.{parts[1]}.{parts[2]}"
    # Resultado: "employees.read.department"
```

### 2. Validación Híbrida
```python
# Verificar si existe el permiso exacto
if permission in discovered_permissions:
    return valid

# Si no existe, verificar permiso base
base_permission = "employees.read"
if base_permission in discovered_permissions:
    # Aceptar permiso granular basado en permiso base
    return valid
```

### 3. Aplicación de Seguridad por Categoría
```python
# Para campos sensibles, verificar permiso de categoría
if field.is_pii:
    require_permission("employees.read.pii")
elif field.is_financial:
    require_permission("employees.read.financial")
elif field.is_phi:
    require_permission("employees.read.phi")
elif field.is_sensitive:
    require_permission("employees.read.sensitive")
else:
    # Campo no sensible, permiso base es suficiente
    require_permission("employees.read")
```

## Casos de Uso Gubernamentales

### 1. Empleado Regular
- Permisos: `employees.read` (base)
- Acceso: Solo campos públicos (nombre, departamento, título)
- Sin acceso a: SSN, salario, información médica

### 2. Recursos Humanos
- Permisos: `employees.read`, `employees.read.pii`
- Acceso: Información personal (dirección, teléfono)
- Sin acceso a: Información financiera o médica

### 3. Nómina
- Permisos: `employees.read`, `employees.read.financial`
- Acceso: Salarios, bonos, deducciones
- Sin acceso a: Información médica

### 4. Administrador
- Permisos: `employees.*` (wildcard)
- Acceso: Todos los campos y acciones

## Configuración de Ejemplo

### HR App - Definición de Roles

```json
{
  "role_name": "HR_Manager",
  "description": "Gerente de Recursos Humanos",
  "permissions": [
    "employees.read",
    "employees.read.pii",
    "employees.write",
    "employees.write.pii",
    "departments.read",
    "departments.write"
  ],
  "ad_group": "AD_HR_Managers"
}
```

### Configuración de Campo Sensible

```sql
-- Marcar campo SSN como PII
UPDATE cids.field_metadata
SET is_pii = true, is_sensitive = true
WHERE resource = 'employees' AND field_name = 'ssn';

-- Marcar campo salario como financiero
UPDATE cids.field_metadata
SET is_financial = true, is_sensitive = true
WHERE resource = 'employees' AND field_name = 'salary';
```

## Ventajas del Sistema Híbrido

### 1. Seguridad Mejorada
- Control granular sobre datos sensibles
- Clasificación automática por tipo de dato
- Auditoría completa de accesos

### 2. Flexibilidad
- Tres niveles de granularidad según necesidad
- Compatible con sistemas legacy (permisos base)
- Escalable para futuras necesidades

### 3. Cumplimiento Normativo
- Separación clara de PII, PHI, y datos financieros
- Trazabilidad completa de permisos
- Cumple con regulaciones gubernamentales

### 4. Facilidad de Administración
- Categorías predefinidas simplifican asignación
- Herencia implícita (base → categoría → campo)
- Dashboard visual para monitoreo

## Migración y Compatibilidad

### Compatibilidad con Sistema Anterior
- Permisos existentes (`resource.action`) siguen funcionando
- Conversión automática de formato frontend (`:` → `.`)
- Sin necesidad de migración masiva

### Pasos de Migración Recomendados

1. **Clasificar campos sensibles** en `field_metadata`
2. **Crear permisos por categoría** en `discovered_permissions`
3. **Actualizar roles gradualmente** agregando permisos granulares
4. **Monitorear** uso mediante activity_log

## Monitoreo y Auditoría

### Registros de Actividad
```sql
-- Ver asignación de permisos
SELECT * FROM cids.activity_log
WHERE activity_type IN ('role.create', 'permission.update')
ORDER BY timestamp DESC;

-- Auditar acceso a datos sensibles
SELECT * FROM cids.activity_log
WHERE details->>'permissions' LIKE '%.pii%'
   OR details->>'permissions' LIKE '%.financial%'
   OR details->>'permissions' LIKE '%.phi%';
```

### Dashboard de Monitoreo
- Total de permisos por rol
- Distribución de permisos por categoría
- Roles sin permisos asignados
- Campos sensibles sin protección

## Consideraciones de Seguridad

### 1. Principio de Menor Privilegio
- Asignar solo permisos necesarios
- Preferir permisos específicos sobre wildcards
- Revisar periódicamente permisos asignados

### 2. Separación de Responsabilidades
- HR no debe tener acceso financiero
- Nómina no debe tener acceso médico
- Auditoría independiente de administración

### 3. Protección de Datos Sensibles
- Todos los campos PII requieren permiso explícito
- Logging automático de acceso a datos sensibles
- Encriptación de datos en reposo y tránsito

## Conclusión

El sistema híbrido de permisos implementado proporciona un balance óptimo entre seguridad, flexibilidad y facilidad de uso. Es especialmente adecuado para entornos gubernamentales que requieren:

- Control granular sobre datos sensibles
- Cumplimiento normativo estricto
- Auditoría completa de accesos
- Escalabilidad para futuras necesidades

El sistema está completamente operativo y listo para uso en producción, con todas las correcciones de bugs implementadas y probadas.

## Anexo: Comandos Útiles

### Limpiar tablas (desarrollo)
```bash
./clean_tables.sh
```

### Ver estadísticas de permisos
```sql
SELECT 
    rm.role_name,
    COUNT(p.permission_id) as permission_count
FROM cids.role_metadata rm
LEFT JOIN cids.permissions p ON rm.role_id = p.role_id
GROUP BY rm.role_name
ORDER BY permission_count DESC;
```

### Verificar permisos de un rol
```sql
SELECT * FROM cids.role_permissions
WHERE client_id = 'app_31a86fe79c7d475b'
AND role_name = 'HR_Manager';
```

### Auditar cambios recientes
```sql
SELECT * FROM cids.activity_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```