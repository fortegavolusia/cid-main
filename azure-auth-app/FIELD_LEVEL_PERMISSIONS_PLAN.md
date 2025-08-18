# CIDS Field-Level Permissions Implementation Plan

## Overview
Transform CIDS from role-based endpoint access to zero-trust field-level permissions.

## Phase 1: Enhanced Discovery Protocol

### 1.1 Update Discovery Models
```python
# discovery_service.py
class FieldMetadata(BaseModel):
    type: str  # string, number, boolean, object, array
    description: Optional[str]
    sensitive: bool = False
    pii: bool = False
    required: bool = False
    fields: Optional[Dict[str, 'FieldMetadata']] = None  # For nested objects

class EnhancedEndpointMetadata(BaseModel):
    method: str
    path: str
    operation_id: str
    description: str
    parameters: List[ParameterMetadata]
    response_fields: Dict[str, FieldMetadata]
    request_fields: Optional[Dict[str, FieldMetadata]] = None
```

### 1.2 Discovery Storage Enhancement
- Extend `app_endpoints.json` to store field metadata
- Create `app_permissions.json` for discovered permissions
- Auto-generate permission keys from discovery

## Phase 2: Permission Structure

### 2.1 Permission Generation
From discovery, auto-generate permissions:
```
GET /api/users/{id} with fields [id, name, email, salary]
Generates:
- app_123.users.read.id
- app_123.users.read.name
- app_123.users.read.email
- app_123.users.read.salary
- app_123.users.read.*  (wildcard for all fields)
```

### 2.2 Permission Storage
```json
{
  "app_8173364316bf4910": {
    "permissions": {
      "users.read.id": {
        "resource": "users",
        "action": "read",
        "field": "id",
        "description": "Read user ID"
      },
      "users.read.salary": {
        "resource": "users",
        "action": "read", 
        "field": "salary",
        "description": "Read user salary",
        "sensitive": true
      }
    }
  }
}
```

## Phase 3: Role Builder Enhancement

### 3.1 New UI Components
- Permission tree view (resource → action → fields)
- Bulk permission assignment
- Permission search/filter
- Visual indicators for sensitive/PII fields

### 3.2 Role Definition Structure
```json
{
  "role_name": "hr_manager",
  "permissions": [
    "app_123.users.read.*",
    "app_123.users.write.salary",
    "app_123.users.write.department",
    "app_123.reports.execute.payroll"
  ]
}
```

## Phase 4: Token Enhancement

### 4.1 Token Claims Structure
```json
{
  "sub": "user123",
  "email": "user@company.com",
  "roles": ["hr_manager", "auditor"],
  "permissions": [
    "app_123.users.read.id",
    "app_123.users.read.name",
    "app_123.users.read.email",
    "app_123.users.read.salary",
    "app_123.users.write.salary"
  ],
  "permission_metadata": {
    "app_123": {
      "version": "2.0",
      "discovered_at": "2024-01-15T10:00:00Z"
    }
  }
}
```

### 4.2 Token Size Optimization
- Use permission compression for large permission sets
- Implement permission inheritance (users.read.* = all read fields)
- Consider JWT size limits (8KB typical)

## Phase 5: Shared Auth Library

### 5.1 Core Functions
```python
# cids_auth.py
class CIDSAuth:
    def __init__(self, cids_url: str, client_id: str):
        self.cids_url = cids_url
        self.client_id = client_id
    
    def require_permissions(*permissions):
        """Decorator to check permissions"""
        
    def filter_response(data: dict, permissions: List[str], resource: str):
        """Filter response based on field permissions"""
        
    def check_field_access(field_path: str, permissions: List[str]) -> bool:
        """Check if user has access to specific field"""
```

## Phase 6: Admin Interface Updates

### 6.1 Discovery Management
- View discovered fields for each endpoint
- Mark fields as sensitive/PII
- Preview permission generation
- Refresh discovery on-demand

### 6.2 Permission Assignment Interface
```
[HR System]
├── users
│   ├── read
│   │   ├── □ Select All
│   │   ├── ✓ id
│   │   ├── ✓ name
│   │   ├── ✓ email
│   │   ├── □ salary (sensitive)
│   │   └── □ ssn (PII)
│   └── write
│       ├── □ Select All
│       ├── ✓ name
│       └── ✓ email
└── reports
    └── execute
        ├── ✓ basic
        └── □ financial (sensitive)
```

## Implementation Steps

1. **Update Discovery Models** (Week 1)
   - Enhance discovery_service.py
   - Update discovery response models
   - Add field metadata support

2. **Permission Generation** (Week 1)
   - Auto-generate permissions from discovery
   - Store in new permission registry
   - Create permission inheritance logic

3. **Database Schema** (Week 2)
   - Design permission storage
   - Implement permission queries
   - Add permission versioning

4. **UI Development** (Week 2-3)
   - Create permission tree component
   - Build role assignment interface
   - Add permission search/filter

5. **Token Generation** (Week 3)
   - Enhance token claims
   - Implement permission compression
   - Add permission metadata

6. **Auth Library** (Week 4)
   - Create cids_auth package
   - Implement decorators
   - Add response filtering

7. **Testing & Documentation** (Week 4)
   - Integration tests
   - Performance testing
   - Update compliance spec

## Migration Strategy

1. Existing apps continue working with role-based permissions
2. New discovery format is backwards compatible
3. Gradual migration as apps implement enhanced discovery
4. Permission-based and role-based can coexist

## Performance Considerations

1. **Token Size**: Monitor JWT size, implement compression if needed
2. **Permission Lookups**: Cache permission checks in apps
3. **Discovery Frequency**: Rate limit discovery calls
4. **Response Filtering**: Optimize for large object filtering

## Security Considerations

1. **Permission Sprawl**: Regular audit of granted permissions
2. **Sensitive Data**: Clear marking and extra logging
3. **Token Leakage**: Short expiry for high-privilege tokens
4. **Audit Trail**: Log all permission grants/denies