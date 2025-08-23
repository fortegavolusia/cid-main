# Token Management MVP - TODO List

## Backend Integration

### 1. Token Template Persistence
- [ ] Replace localStorage with backend database storage
- [ ] Create database schema for token templates table
  - Template ID, name, description
  - Claims JSON structure
  - AD group associations
  - Priority and enabled flags
  - Created/updated timestamps
  - Created by user

### 2. API Endpoints Implementation
- [ ] Implement GET `/auth/admin/token-templates` - fetch all templates
- [ ] Implement POST `/auth/admin/token-templates` - create/update template
- [ ] Implement DELETE `/auth/admin/token-templates/{template_name}` - delete template
- [ ] Add authentication/authorization checks for admin endpoints
- [ ] Add validation for template structure and claims

### 3. Token Generation Integration
- [ ] Test template application during JWT token creation
- [ ] Verify AD group matching logic works with real Azure tokens
- [ ] Test priority system when multiple templates match
- [ ] Validate custom claims are properly added to tokens
- [ ] Ensure backward compatibility with existing tokens

## Frontend Enhancements

### 4. Token Builder Improvements
- [ ] Add validation for claim keys (no spaces, valid characters)
- [ ] Add ability to reorder claims (drag and drop)
- [ ] Add nested object/array support for complex claims
- [ ] Add claim value preview/examples
- [ ] Add undo/redo functionality
- [ ] Implement save as new template (clone) feature

### 5. Template Management
- [ ] Add template versioning/history
- [ ] Add bulk operations (enable/disable multiple templates)
- [ ] Add template usage statistics (how many tokens used this template)
- [ ] Add template testing with mock user data
- [ ] Add template comparison view (diff between templates)

### 6. Azure AD Integration Testing
- [ ] Test with real Azure AD groups from production
- [ ] Handle edge cases (users with no groups, many groups)
- [ ] Test group search performance with large AD
- [ ] Add group validation (ensure groups exist in AD)
- [ ] Add group membership preview (show users in group)

## Testing & Validation

### 7. Testing Tab Implementation
- [ ] Complete the "Testing" tab UI (currently shows "Coming Soon")
- [ ] Add test token generation with sample data
- [ ] Add JWT decoder to preview generated tokens
- [ ] Add validation against schema
- [ ] Add performance testing (token generation time)
- [ ] Add batch testing with multiple user scenarios

### 8. Settings Tab Implementation
- [ ] Complete the "Settings" tab UI (currently shows "Coming Soon")
- [ ] Add token expiration configuration
- [ ] Add signing algorithm selection (RS256, HS256, etc.)
- [ ] Add default claims configuration
- [ ] Add token size limits/warnings
- [ ] Add refresh token configuration

## Security & Compliance

### 9. Security Enhancements
- [ ] Add audit logging for template changes
- [ ] Add role-based access control for template management
- [ ] Implement template approval workflow (optional)
- [ ] Add sensitive claim marking/encryption
- [ ] Add token signing key rotation support

### 10. Validation & Error Handling
- [ ] Add comprehensive error messages for template issues
- [ ] Add claim conflict detection (duplicate keys)
- [ ] Add template syntax validation
- [ ] Add size limit checks (JWT token size)
- [ ] Add circular reference detection in nested claims

## Documentation & Deployment

### 11. Documentation
- [ ] Create user guide for Token Administration
- [ ] Document template JSON schema
- [ ] Add API documentation for token template endpoints
- [ ] Create migration guide from current tokens to templates
- [ ] Add troubleshooting guide

### 12. Deployment Preparation
- [ ] Add database migration scripts
- [ ] Update deployment configuration
- [ ] Add feature flags for gradual rollout
- [ ] Create rollback plan
- [ ] Add monitoring/alerting for template usage

## Performance & Optimization

### 13. Performance
- [ ] Implement template caching in backend
- [ ] Optimize AD group lookup queries
- [ ] Add pagination for template list (if many templates)
- [ ] Implement lazy loading for template preview
- [ ] Add debouncing for all API calls

### 14. User Experience
- [ ] Add loading states for all async operations
- [ ] Add confirmation dialogs for destructive actions
- [ ] Add keyboard shortcuts for common actions
- [ ] Add template search/filter persistence
- [ ] Add recently used templates section

## Integration & Compatibility

### 15. System Integration
- [ ] Test with existing CIDS authentication flow
- [ ] Verify compatibility with current JWT consumers
- [ ] Test with FastAPI test applications
- [ ] Validate with row-level security (RLS) system
- [ ] Ensure backward compatibility

## MVP Priority Items (Must Have)

### Phase 1 - Core Functionality ⚡
1. Backend database storage for templates
2. Working API endpoints with basic CRUD
3. Template application during token generation
4. AD group matching and template selection
5. Basic testing functionality

### Phase 2 - Essential Features 🎯
1. Template validation and error handling
2. Audit logging for changes
3. Basic settings (expiration, algorithm)
4. Documentation for admins
5. Integration testing with real AD groups

### Phase 3 - Polish & Deploy 🚀
1. Performance optimization
2. Loading states and error messages
3. Deployment scripts and configuration
4. Monitoring and alerting
5. User guide and training materials

## Notes
- Priority should be given to Phase 1 items for true MVP
- Phase 2 items should follow immediately after
- Phase 3 items can be rolled out post-MVP
- Consider feature flags for gradual rollout of new functionality
- Ensure all changes maintain backward compatibility with existing tokens

## Success Criteria
- [ ] Admins can create and manage token templates via UI
- [ ] Templates are automatically applied based on AD groups
- [ ] Token generation time remains under 100ms
- [ ] No breaking changes to existing token consumers
- [ ] Full audit trail of template changes
- [ ] Documentation complete for admin users