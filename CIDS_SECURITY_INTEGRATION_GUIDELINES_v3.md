# CIDS Security Integration Guidelines / Guía de Integración de Seguridad CIDS
## Version 3.0 - Complete Security Implementation / Versión 3.0 - Implementación Completa de Seguridad

---

# English Version

## Table of Contents
1. [Overview](#overview)
2. [API Keys](#api-keys)
3. [A2A (Application-to-Application) Authentication](#a2a-authentication)
4. [Public Keys and JWT Validation](#public-keys-jwt)
5. [Complete Security Architecture](#security-architecture)
6. [Implementation Guide](#implementation-guide)

---

## 1. Overview

CIDS (Centralized Identity Discovery Service) provides three complementary authentication mechanisms:

- **API Keys**: Long-lived credentials for service identification
- **A2A Service Tokens**: Short-lived JWT tokens for service-to-service communication
- **Public Key Infrastructure**: RSA key pairs for JWT signing and validation

### Key Principles
- **Zero Trust**: Every request is verified independently
- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Minimal permissions granted
- **Complete Audit Trail**: All operations logged

## 2. API Keys

### 2.1 What are API Keys?

API Keys are long-lived credentials (30-90 days) that identify a service to CIDS. They are used for:
- Service authentication
- Batch operations
- Background processes
- Initial authentication before requesting service tokens

### 2.2 API Key Format
```
cids_ak_{32_character_alphanumeric}
Example: cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV
```

### 2.3 API Key Lifecycle

#### Generation
```bash
# Only through CIDS Admin UI or API
POST /auth/admin/apps/{client_id}/api-key
Authorization: Bearer {admin_token}
```

#### Usage
```python
# In service configuration
CIDS_API_KEY = "cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# In requests
headers = {
    "X-API-Key": CIDS_API_KEY
}
```

#### Validation
```python
# CIDS validates API key
async def validate_api_key(key: str) -> dict:
    # Check format
    if not key.startswith("cids_ak_"):
        return {"valid": False}

    # Check in database
    key_id = key.replace("cids_ak_", "")
    result = db.query("SELECT * FROM api_keys WHERE key_id = %s", key_id)

    # Update usage statistics
    db.update("UPDATE api_keys SET last_used_at = NOW(), usage_count = usage_count + 1")

    return {"valid": True, "client_id": result["client_id"]}
```

### 2.4 API Key Security Rules

1. **One Active Key Per Service**: Creating a new key deactivates the old one
2. **Automatic Rotation**: Keys expire after 90 days
3. **Usage Tracking**: Every use is logged
4. **IP Restrictions**: Optional IP whitelist
5. **Revocation**: Immediate deactivation on compromise

## 3. A2A (Application-to-Application) Authentication

### 3.1 What is A2A?

A2A provides secure service-to-service communication using temporary JWT tokens (5-10 minutes). It's designed for:
- Microservices communication
- Cross-service API calls
- Zero Trust architecture
- Granular permission control

### 3.2 A2A vs API Keys

| Feature | API Key | A2A Service Token |
|---------|---------|-------------------|
| **Lifetime** | 30-90 days | 5-10 minutes |
| **Purpose** | Service identification | Specific operations |
| **Scopes** | Fixed | Dynamic per request |
| **Validation** | Simple key check | JWT signature + claims |
| **Revocation** | Manual | Automatic expiry |
| **Use Case** | Background jobs | Service-to-service calls |

### 3.3 A2A Flow

```mermaid
sequenceDiagram
    participant HR as HR System
    participant CIDS as CIDS
    participant Bank as Bank System

    HR->>CIDS: POST /auth/service-token<br/>X-API-Key: {HR_API_KEY}
    Note over CIDS: Validate API key<br/>Check A2A permission<br/>Generate JWT token
    CIDS-->>HR: JWT Service Token (5 min)

    HR->>Bank: GET /accounts/{id}<br/>Authorization: Bearer {SERVICE_TOKEN}
    Bank->>CIDS: POST /auth/validate<br/>Token: {SERVICE_TOKEN}
    CIDS-->>Bank: Valid + Claims
    Note over Bank: Verify audience<br/>Check scopes
    Bank-->>HR: Account data
```

### 3.4 A2A Configuration

#### Database Schema
```sql
CREATE TABLE cids.a2a_permissions (
    a2a_id VARCHAR(50) PRIMARY KEY,
    source_client_id VARCHAR(50) NOT NULL,
    target_client_id VARCHAR(50) NOT NULL,
    allowed_scopes TEXT[] DEFAULT '{}',
    allowed_endpoints TEXT[] DEFAULT '{}',
    max_token_duration INTEGER DEFAULT 300,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    FOREIGN KEY (source_client_id) REFERENCES registered_apps(client_id),
    FOREIGN KEY (target_client_id) REFERENCES registered_apps(client_id),
    UNIQUE(source_client_id, target_client_id)
);
```

#### Creating A2A Permission
```bash
POST /auth/admin/a2a/permissions
{
    "source_client_id": "app_hr_system",
    "target_client_id": "app_bank_system",
    "allowed_scopes": ["accounts.read", "accounts.balance"],
    "allowed_endpoints": ["/accounts/*/balance"],
    "max_token_duration": 600
}
```

### 3.5 Service Token Request

```python
# HR System requests token to call Bank
async def get_service_token(target: str, scopes: list) -> str:
    response = await httpx.post(
        f"{CIDS_URL}/auth/service-token",
        headers={"X-API-Key": HR_API_KEY},
        json={
            "target_client_id": target,
            "requested_scopes": scopes,
            "duration": 300,
            "purpose": "Payroll processing"
        }
    )
    return response.json()["token"]
```

### 3.6 Service Token Validation

```python
# Bank System validates incoming token
async def validate_service_token(token: str) -> dict:
    response = await httpx.post(
        f"{CIDS_URL}/auth/validate",
        json={"token": token}
    )

    claims = response.json()["claims"]

    # Verify audience
    if BANK_CLIENT_ID not in claims["aud"]:
        raise Exception("Token not for this service")

    # Check token type
    if claims.get("type") == "service_token":
        log_a2a_access(claims["sub"], claims["a2a_id"])

    return claims
```

## 4. Public Keys and JWT Validation

### 4.1 RSA Key Pairs

CIDS uses RSA-256 for JWT signing:

```python
# Key generation (CIDS internal)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

public_key = private_key.public_key()
```

### 4.2 JWKS Endpoint

Public keys are available at:
```
GET /.well-known/jwks.json
```

Response:
```json
{
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "kid": "auth-service-key-1",
            "n": "base64_encoded_modulus",
            "e": "AQAB",
            "alg": "RS256"
        }
    ]
}
```

### 4.3 JWT Token Structure

```json
{
    "header": {
        "alg": "RS256",
        "kid": "auth-service-key-1",
        "typ": "JWT"
    },
    "payload": {
        "iss": "internal-auth-service",
        "sub": "app_hr_system",
        "aud": "app_bank_system",
        "exp": 1234567890,
        "iat": 1234567590,
        "jti": "unique_token_id",
        "type": "service_token",
        "a2a_id": "a2a_hr_to_bank_001",
        "scopes": ["accounts.read"],
        "purpose": "Payroll processing"
    },
    "signature": "base64_encoded_signature"
}
```

### 4.4 Token Validation Process

```python
import jwt
from jwt import PyJWKClient

# Get public key from CIDS
jwks_client = PyJWKClient(f"{CIDS_URL}/.well-known/jwks.json")

def validate_token(token: str) -> dict:
    # Get signing key
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # Verify signature and decode
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=OUR_CLIENT_ID,
        issuer="internal-auth-service"
    )

    # Additional validations
    if claims["exp"] < time.time():
        raise Exception("Token expired")

    return claims
```

## 5. Complete Security Architecture

### 5.1 Three-Layer Security Model

```
┌─────────────────────────────────────────────┐
│            Layer 1: API Keys                 │
│  Long-lived service identification          │
├─────────────────────────────────────────────┤
│        Layer 2: A2A Service Tokens          │
│  Short-lived operation-specific tokens      │
├─────────────────────────────────────────────┤
│         Layer 3: Public Key Crypto          │
│  RSA-256 signature verification             │
└─────────────────────────────────────────────┘
```

### 5.2 Security Flow Example

```python
# Complete secure communication example

# 1. Service authenticates with API key
api_key = "cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# 2. Request service token for specific operation
service_token = request_service_token(
    api_key=api_key,
    target="app_bank_system",
    scopes=["accounts.read"],
    duration=300
)

# 3. Use service token for API call
response = call_bank_api(
    endpoint="/accounts/123/balance",
    token=service_token
)

# 4. Bank validates token using public key
claims = validate_jwt_with_public_key(service_token)

# 5. Bank checks audience and scopes
if "app_bank_system" in claims["aud"]:
    if "accounts.read" in claims["scopes"]:
        return account_data
```

## 6. Implementation Guide

### 6.1 Setting Up API Keys

```bash
# 1. Register your application in CIDS
POST /auth/admin/apps
{
    "name": "My Service",
    "client_id": "app_my_service",
    "discovery_endpoint": "http://my-service:8000/discovery/endpoints"
}

# 2. Generate API key
POST /auth/admin/apps/app_my_service/api-key

# 3. Store in environment
export CIDS_API_KEY="cids_ak_..."
```

### 6.2 Implementing A2A

```python
# service_a.py (Source service)
class ServiceA:
    def __init__(self):
        self.api_key = os.getenv("SERVICE_A_API_KEY")
        self.cids_url = os.getenv("CIDS_URL")

    async def call_service_b(self, data):
        # Get service token
        token = await self.get_service_token("app_service_b")

        # Call Service B
        response = await httpx.post(
            "http://service-b/api/endpoint",
            headers={"Authorization": f"Bearer {token}"},
            json=data
        )
        return response.json()

# service_b.py (Target service)
class ServiceB:
    async def validate_request(self, authorization: str):
        token = authorization.replace("Bearer ", "")

        # Validate with CIDS
        validation = await httpx.post(
            f"{CIDS_URL}/auth/validate",
            json={"token": token}
        )

        if not validation.json()["valid"]:
            raise HTTPException(401)

        claims = validation.json()["claims"]

        # Verify audience
        if "app_service_b" not in claims.get("aud", []):
            raise HTTPException(403, "Wrong audience")

        return claims
```

### 6.3 Public Key Validation

```python
import httpx
from jose import jwt, JWTError

class TokenValidator:
    def __init__(self, cids_url: str):
        self.cids_url = cids_url
        self._public_keys = None

    async def get_public_keys(self):
        if not self._public_keys:
            response = await httpx.get(f"{self.cids_url}/.well-known/jwks.json")
            self._public_keys = response.json()["keys"]
        return self._public_keys

    async def validate_token(self, token: str) -> dict:
        try:
            # Get public keys
            keys = await self.get_public_keys()

            # Decode and verify
            header = jwt.get_unverified_header(token)
            key = next(k for k in keys if k["kid"] == header["kid"])

            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id
            )

            return {"valid": True, "claims": claims}
        except JWTError as e:
            return {"valid": False, "error": str(e)}
```

---

# Versión en Español

## Tabla de Contenidos
1. [Resumen General](#resumen-general)
2. [API Keys](#api-keys-es)
3. [Autenticación A2A (Aplicación a Aplicación)](#autenticacion-a2a)
4. [Llaves Públicas y Validación JWT](#llaves-publicas-jwt)
5. [Arquitectura de Seguridad Completa](#arquitectura-seguridad)
6. [Guía de Implementación](#guia-implementacion)

---

## 1. Resumen General

CIDS (Servicio Centralizado de Descubrimiento de Identidad) proporciona tres mecanismos de autenticación complementarios:

- **API Keys**: Credenciales de larga duración para identificación de servicios
- **Tokens de Servicio A2A**: Tokens JWT de corta duración para comunicación entre servicios
- **Infraestructura de Llave Pública**: Pares de llaves RSA para firma y validación de JWT

### Principios Clave
- **Confianza Cero**: Cada solicitud se verifica independientemente
- **Defensa en Profundidad**: Múltiples capas de seguridad
- **Privilegio Mínimo**: Se otorgan permisos mínimos
- **Auditoría Completa**: Todas las operaciones se registran

## 2. API Keys

### 2.1 ¿Qué son las API Keys?

Las API Keys son credenciales de larga duración (30-90 días) que identifican un servicio ante CIDS. Se usan para:
- Autenticación de servicios
- Operaciones batch
- Procesos en segundo plano
- Autenticación inicial antes de solicitar tokens de servicio

### 2.2 Formato de API Key
```
cids_ak_{32_caracteres_alfanuméricos}
Ejemplo: cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV
```

### 2.3 Ciclo de Vida de API Key

#### Generación
```bash
# Solo a través de la UI Admin de CIDS o API
POST /auth/admin/apps/{client_id}/api-key
Authorization: Bearer {token_admin}
```

#### Uso
```python
# En la configuración del servicio
CIDS_API_KEY = "cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# En las solicitudes
headers = {
    "X-API-Key": CIDS_API_KEY
}
```

#### Validación
```python
# CIDS valida la API key
async def validar_api_key(key: str) -> dict:
    # Verificar formato
    if not key.startswith("cids_ak_"):
        return {"valid": False}

    # Verificar en base de datos
    key_id = key.replace("cids_ak_", "")
    result = db.query("SELECT * FROM api_keys WHERE key_id = %s", key_id)

    # Actualizar estadísticas de uso
    db.update("UPDATE api_keys SET last_used_at = NOW(), usage_count = usage_count + 1")

    return {"valid": True, "client_id": result["client_id"]}
```

### 2.4 Reglas de Seguridad de API Key

1. **Una Llave Activa Por Servicio**: Crear una nueva desactiva la anterior
2. **Rotación Automática**: Las llaves expiran después de 90 días
3. **Seguimiento de Uso**: Cada uso se registra
4. **Restricciones de IP**: Lista blanca de IP opcional
5. **Revocación**: Desactivación inmediata en caso de compromiso

## 3. Autenticación A2A (Aplicación a Aplicación)

### 3.1 ¿Qué es A2A?

A2A proporciona comunicación segura entre servicios usando tokens JWT temporales (5-10 minutos). Está diseñado para:
- Comunicación entre microservicios
- Llamadas API entre servicios
- Arquitectura de Confianza Cero
- Control granular de permisos

### 3.2 A2A vs API Keys

| Característica | API Key | Token de Servicio A2A |
|----------------|---------|----------------------|
| **Duración** | 30-90 días | 5-10 minutos |
| **Propósito** | Identificación de servicio | Operaciones específicas |
| **Alcances** | Fijos | Dinámicos por solicitud |
| **Validación** | Verificación simple | Firma JWT + claims |
| **Revocación** | Manual | Expiración automática |
| **Caso de Uso** | Trabajos en segundo plano | Llamadas entre servicios |

### 3.3 Flujo A2A

```mermaid
sequenceDiagram
    participant HR as Sistema HR
    participant CIDS as CIDS
    participant Bank as Sistema Bancario

    HR->>CIDS: POST /auth/service-token<br/>X-API-Key: {HR_API_KEY}
    Note over CIDS: Validar API key<br/>Verificar permiso A2A<br/>Generar token JWT
    CIDS-->>HR: Token de Servicio JWT (5 min)

    HR->>Bank: GET /accounts/{id}<br/>Authorization: Bearer {SERVICE_TOKEN}
    Bank->>CIDS: POST /auth/validate<br/>Token: {SERVICE_TOKEN}
    CIDS-->>Bank: Válido + Claims
    Note over Bank: Verificar audience<br/>Verificar scopes
    Bank-->>HR: Datos de cuenta
```

### 3.4 Configuración A2A

#### Esquema de Base de Datos
```sql
CREATE TABLE cids.a2a_permissions (
    a2a_id VARCHAR(50) PRIMARY KEY,
    source_client_id VARCHAR(50) NOT NULL,
    target_client_id VARCHAR(50) NOT NULL,
    allowed_scopes TEXT[] DEFAULT '{}',
    allowed_endpoints TEXT[] DEFAULT '{}',
    max_token_duration INTEGER DEFAULT 300,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    FOREIGN KEY (source_client_id) REFERENCES registered_apps(client_id),
    FOREIGN KEY (target_client_id) REFERENCES registered_apps(client_id),
    UNIQUE(source_client_id, target_client_id)
);
```

#### Crear Permiso A2A
```bash
POST /auth/admin/a2a/permissions
{
    "source_client_id": "app_sistema_hr",
    "target_client_id": "app_sistema_banco",
    "allowed_scopes": ["accounts.read", "accounts.balance"],
    "allowed_endpoints": ["/accounts/*/balance"],
    "max_token_duration": 600
}
```

### 3.5 Solicitud de Token de Servicio

```python
# Sistema HR solicita token para llamar a Banco
async def obtener_token_servicio(destino: str, alcances: list) -> str:
    response = await httpx.post(
        f"{CIDS_URL}/auth/service-token",
        headers={"X-API-Key": HR_API_KEY},
        json={
            "target_client_id": destino,
            "requested_scopes": alcances,
            "duration": 300,
            "purpose": "Procesamiento de nómina"
        }
    )
    return response.json()["token"]
```

### 3.6 Validación de Token de Servicio

```python
# Sistema Bancario valida token entrante
async def validar_token_servicio(token: str) -> dict:
    response = await httpx.post(
        f"{CIDS_URL}/auth/validate",
        json={"token": token}
    )

    claims = response.json()["claims"]

    # Verificar audience
    if BANK_CLIENT_ID not in claims["aud"]:
        raise Exception("Token no es para este servicio")

    # Verificar tipo de token
    if claims.get("type") == "service_token":
        registrar_acceso_a2a(claims["sub"], claims["a2a_id"])

    return claims
```

## 4. Llaves Públicas y Validación JWT

### 4.1 Pares de Llaves RSA

CIDS usa RSA-256 para firmar JWT:

```python
# Generación de llaves (interno de CIDS)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

llave_privada = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

llave_publica = llave_privada.public_key()
```

### 4.2 Endpoint JWKS

Las llaves públicas están disponibles en:
```
GET /.well-known/jwks.json
```

Respuesta:
```json
{
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "kid": "auth-service-key-1",
            "n": "modulo_codificado_base64",
            "e": "AQAB",
            "alg": "RS256"
        }
    ]
}
```

### 4.3 Estructura del Token JWT

```json
{
    "header": {
        "alg": "RS256",
        "kid": "auth-service-key-1",
        "typ": "JWT"
    },
    "payload": {
        "iss": "internal-auth-service",
        "sub": "app_sistema_hr",
        "aud": "app_sistema_banco",
        "exp": 1234567890,
        "iat": 1234567590,
        "jti": "id_token_unico",
        "type": "service_token",
        "a2a_id": "a2a_hr_a_banco_001",
        "scopes": ["accounts.read"],
        "purpose": "Procesamiento de nómina"
    },
    "signature": "firma_codificada_base64"
}
```

### 4.4 Proceso de Validación de Token

```python
import jwt
from jwt import PyJWKClient

# Obtener llave pública de CIDS
jwks_client = PyJWKClient(f"{CIDS_URL}/.well-known/jwks.json")

def validar_token(token: str) -> dict:
    # Obtener llave de firma
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # Verificar firma y decodificar
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=NUESTRO_CLIENT_ID,
        issuer="internal-auth-service"
    )

    # Validaciones adicionales
    if claims["exp"] < time.time():
        raise Exception("Token expirado")

    return claims
```

## 5. Arquitectura de Seguridad Completa

### 5.1 Modelo de Seguridad de Tres Capas

```
┌─────────────────────────────────────────────┐
│            Capa 1: API Keys                  │
│  Identificación de servicio de larga vida    │
├─────────────────────────────────────────────┤
│      Capa 2: Tokens de Servicio A2A         │
│  Tokens específicos de operación corta vida  │
├─────────────────────────────────────────────┤
│       Capa 3: Criptografía Llave Pública    │
│  Verificación de firma RSA-256              │
└─────────────────────────────────────────────┘
```

### 5.2 Ejemplo de Flujo de Seguridad

```python
# Ejemplo completo de comunicación segura

# 1. Servicio se autentica con API key
api_key = "cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# 2. Solicitar token de servicio para operación específica
token_servicio = solicitar_token_servicio(
    api_key=api_key,
    destino="app_sistema_banco",
    alcances=["accounts.read"],
    duracion=300
)

# 3. Usar token de servicio para llamada API
respuesta = llamar_api_banco(
    endpoint="/accounts/123/balance",
    token=token_servicio
)

# 4. Banco valida token usando llave pública
claims = validar_jwt_con_llave_publica(token_servicio)

# 5. Banco verifica audience y alcances
if "app_sistema_banco" in claims["aud"]:
    if "accounts.read" in claims["scopes"]:
        return datos_cuenta
```

## 6. Guía de Implementación

### 6.1 Configurando API Keys

```bash
# 1. Registrar tu aplicación en CIDS
POST /auth/admin/apps
{
    "name": "Mi Servicio",
    "client_id": "app_mi_servicio",
    "discovery_endpoint": "http://mi-servicio:8000/discovery/endpoints"
}

# 2. Generar API key
POST /auth/admin/apps/app_mi_servicio/api-key

# 3. Guardar en ambiente
export CIDS_API_KEY="cids_ak_..."
```

### 6.2 Implementando A2A

```python
# servicio_a.py (Servicio origen)
class ServicioA:
    def __init__(self):
        self.api_key = os.getenv("SERVICIO_A_API_KEY")
        self.cids_url = os.getenv("CIDS_URL")

    async def llamar_servicio_b(self, datos):
        # Obtener token de servicio
        token = await self.obtener_token_servicio("app_servicio_b")

        # Llamar Servicio B
        response = await httpx.post(
            "http://servicio-b/api/endpoint",
            headers={"Authorization": f"Bearer {token}"},
            json=datos
        )
        return response.json()

# servicio_b.py (Servicio destino)
class ServicioB:
    async def validar_solicitud(self, authorization: str):
        token = authorization.replace("Bearer ", "")

        # Validar con CIDS
        validacion = await httpx.post(
            f"{CIDS_URL}/auth/validate",
            json={"token": token}
        )

        if not validacion.json()["valid"]:
            raise HTTPException(401)

        claims = validacion.json()["claims"]

        # Verificar audience
        if "app_servicio_b" not in claims.get("aud", []):
            raise HTTPException(403, "Audience incorrecto")

        return claims
```

### 6.3 Validación con Llave Pública

```python
import httpx
from jose import jwt, JWTError

class ValidadorToken:
    def __init__(self, cids_url: str):
        self.cids_url = cids_url
        self._llaves_publicas = None

    async def obtener_llaves_publicas(self):
        if not self._llaves_publicas:
            response = await httpx.get(f"{self.cids_url}/.well-known/jwks.json")
            self._llaves_publicas = response.json()["keys"]
        return self._llaves_publicas

    async def validar_token(self, token: str) -> dict:
        try:
            # Obtener llaves públicas
            llaves = await self.obtener_llaves_publicas()

            # Decodificar y verificar
            header = jwt.get_unverified_header(token)
            llave = next(k for k in llaves if k["kid"] == header["kid"])

            claims = jwt.decode(
                token,
                llave,
                algorithms=["RS256"],
                audience=self.client_id
            )

            return {"valid": True, "claims": claims}
        except JWTError as e:
            return {"valid": False, "error": str(e)}
```

---

## Testing Commands / Comandos de Prueba

### English

```bash
# Test API Key validation
curl -X GET http://localhost:8001/auth/validate \
  -H "Authorization: Bearer cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# Request A2A service token
curl -X POST http://localhost:8001/auth/service-token \
  -H "X-API-Key: cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV" \
  -H "Content-Type: application/json" \
  -d '{
    "target_client_id": "app_bank_system",
    "requested_scopes": ["accounts.read"],
    "duration": 300
  }'

# Get public keys
curl http://localhost:8001/.well-known/jwks.json
```

### Español

```bash
# Probar validación de API Key
curl -X GET http://localhost:8001/auth/validate \
  -H "Authorization: Bearer cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"

# Solicitar token de servicio A2A
curl -X POST http://localhost:8001/auth/service-token \
  -H "X-API-Key: cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV" \
  -H "Content-Type: application/json" \
  -d '{
    "target_client_id": "app_sistema_banco",
    "requested_scopes": ["accounts.read"],
    "duration": 300
  }'

# Obtener llaves públicas
curl http://localhost:8001/.well-known/jwks.json
```

---

## Security Best Practices / Mejores Prácticas de Seguridad

### English
1. **Never share API keys** between services
2. **Rotate API keys** every 90 days
3. **Use A2A tokens** for service-to-service calls
4. **Validate JWT signatures** with public keys
5. **Check token audience** matches your service
6. **Log all authentication** attempts
7. **Implement rate limiting** on all endpoints
8. **Use HTTPS** in production
9. **Store keys in environment** variables, never in code
10. **Monitor for anomalies** in authentication patterns

### Español
1. **Nunca compartir API keys** entre servicios
2. **Rotar API keys** cada 90 días
3. **Usar tokens A2A** para llamadas entre servicios
4. **Validar firmas JWT** con llaves públicas
5. **Verificar que audience** coincida con tu servicio
6. **Registrar todos los intentos** de autenticación
7. **Implementar limitación de tasa** en todos los endpoints
8. **Usar HTTPS** en producción
9. **Guardar llaves en variables** de entorno, nunca en código
10. **Monitorear anomalías** en patrones de autenticación

---

## Support / Soporte

**English:**
- Security Team: security@cids.gov
- Technical Support: support@cids.gov
- Documentation: https://docs.cids.gov

**Español:**
- Equipo de Seguridad: seguridad@cids.gov
- Soporte Técnico: soporte@cids.gov
- Documentación: https://docs.cids.gov/es

---

**Document Version:** 3.0
**Last Updated:** September 2025
**Classification:** OFFICIAL USE

---