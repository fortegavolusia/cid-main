# Security Compliance - Hybrid Permission System

## System Overview
The CID (Centralized Identity Discovery) system implements a hybrid permission model with automatic categorization based on field sensitivity. This architecture ensures compliance with multiple security standards and regulations.

## Compliance Standards Met

### 1. GDPR (General Data Protection Regulation)
- **Data Minimization**: Access only to necessary fields based on category
- **Privacy by Design**: Architecture separates sensitive data (PII, PHI) from design
- **Granular Control**: Enables compliance with limited personal data access rights
- **Articles Addressed**: Art. 5(1)(c), Art. 25, Art. 32

### 2. HIPAA (Health Insurance Portability and Accountability Act)
- **PHI Protection**: Specific category for Protected Health Information
- **Minimum Necessary Standard**: Access only to strictly necessary medical information
- **Audit Trails**: System logs who accesses which data category
- **Sections Addressed**: §164.502(b), §164.514(d), §164.312(a)

### 3. PCI DSS (Payment Card Industry Data Security Standard)
- **Financial Category**: Separates financial and card data
- **Role-based Access**: Access control based on roles
- **Need-to-know Basis**: Financial data access only when necessary
- **Requirements Met**: Req 7.1, 7.2, 8.1, 10.1

### 4. ISO 27001/27002
- **A.9 Access Control**: Implements granular access control
- **A.12.1 Operational Procedures**: Separation of environments and data
- **A.18.1 Compliance**: Facilitates regulatory compliance
- **A.8.2 Information Classification**: Automatic data classification

### 5. NIST Cybersecurity Framework
- **PR.AC (Protect - Access Control)**:
  - PR.AC-1: Managed identities and credentials for authorized users
  - PR.AC-4: Permissions managed with least privilege principle
- **PR.DS (Protect - Data Security)**:
  - PR.DS-1: Protected data at rest
  - PR.DS-5: Protection against data leaks

### 6. SOC 2 Type II
- **Logical Access Controls**: Logical access control to different categories
- **Segregation of Duties**: Separation of responsibilities by categories
- **Data Classification**: Automatic classification of sensitive data
- **Trust Service Criteria**: CC6.1, CC6.2, CC6.3

### 7. California Consumer Privacy Act (CCPA)
- **Data Inventory**: Clear categorization of personal information
- **Access Rights**: Granular control for consumer data access
- **Data Protection**: Segregation of sensitive personal information

## Security Principles Implemented

### Least Privilege
- Access only to necessary categories
- Progressive permission model: base → pii → phi → financial → sensitive → wildcard

### Defense in Depth
- Multiple security layers through category hierarchy
- Each level adds additional access rights

### Zero Trust Architecture
- Continuous verification of permissions by category
- No implicit trust based on network location

### Data Loss Prevention (DLP)
- Prevents accidental exposure of sensitive data
- Clear boundaries between data categories

### Segregation of Sensitive Data
- Clear separation between public and sensitive data
- Automatic categorization based on field metadata

## Permission Categories

### 1. Base
- Non-sensitive, public information
- No PII, PHI, or financial data
- Lowest access level

### 2. PII (Personally Identifiable Information)
- Fields marked with `is_pii: true`
- Includes: SSN, email, phone, address
- GDPR/CCPA relevant data

### 3. PHI (Protected Health Information)
- Fields marked with `is_phi: true`
- Medical records, health conditions
- HIPAA protected data

### 4. Financial
- Fields marked with `is_financial: true`
- Credit cards, bank accounts, salary
- PCI DSS relevant data

### 5. Sensitive
- Fields marked with `is_sensitive: true`
- Combination of multiple sensitivity types
- Highest regular access level

### 6. Wildcard
- All fields including highly sensitive
- Administrative access only
- Complete data access

## Implementation Architecture

### Database Schema
```sql
-- Permissions table with category column
CREATE TABLE cids.permissions (
    permission_id UUID PRIMARY KEY,
    role_id UUID,
    resource VARCHAR(255),
    action VARCHAR(50),
    category VARCHAR(50), -- base, pii, phi, financial, sensitive, wildcard
    fields JSONB,
    resource_filters JSONB,
    per_id VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Field metadata for sensitivity classification
CREATE TABLE cids.field_metadata (
    id UUID PRIMARY KEY,
    app_id VARCHAR(255),
    endpoint VARCHAR(255),
    field_name VARCHAR(255),
    is_pii BOOLEAN DEFAULT FALSE,
    is_phi BOOLEAN DEFAULT FALSE,
    is_financial BOOLEAN DEFAULT FALSE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Discovery Process
1. **Step 1**: Initial endpoint discovery
2. **Step 2**: Permission discovery (base permissions)
3. **Step 3**: Field metadata collection
4. **Step 4**: Save field sensitivity information
5. **Step 5**: Role and permission mapping
6. **Step 6**: Automatic category generation based on field sensitivity

### JWT Token Structure
```json
{
  "roles": {
    "app_id": ["role1", "role2"]
  },
  "permissions": {
    "app_id": [
      "resource.action.category"
    ]
  },
  "rls_filters": {
    "resource.action": {
      "field": "SQL WHERE clause"
    }
  }
}
```

## Compliance Benefits

### 1. Simplified Auditing
- Clear demonstration of which roles access which data types
- Audit trail of permission assignments
- Category-based access reports

### 2. Compliance Reporting
- Clear reports on sensitive data access
- Automated compliance dashboards
- Real-time access monitoring

### 3. Risk Management
- Reduced risk of sensitive data exposure
- Clear data classification
- Automated sensitivity detection

### 4. Data Governance
- Clear data governance by categories
- Automated data classification
- Consistent access policies

### 5. Privacy Protection
- Enhanced user privacy protection
- Granular consent management
- Data minimization by default

## Audit and Monitoring

### Access Logs
- Every permission check is logged
- Category-based access tracking
- Anomaly detection capabilities

### Compliance Reports
- Daily/Weekly/Monthly access reports
- Sensitive data access summaries
- Role utilization reports

### Alert System
- Unauthorized access attempts
- Privilege escalation detection
- Sensitive data access alerts

## Best Practices

1. **Regular Permission Reviews**
   - Quarterly role audits
   - Remove unnecessary permissions
   - Validate category assignments

2. **Training and Awareness**
   - Role-based security training
   - Data classification education
   - Compliance requirement updates

3. **Continuous Improvement**
   - Regular security assessments
   - Compliance gap analysis
   - System optimization

## Version History
- v1.0 (2025-01): Initial hybrid permission system
- v1.1 (2025-01): Added automatic category generation
- v1.2 (2025-01): Enhanced UI with permission matrix

## Contact
For security and compliance inquiries, contact the IT Security team.