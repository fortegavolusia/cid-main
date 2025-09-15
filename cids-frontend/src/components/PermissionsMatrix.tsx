import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

/*
 * OTRAS OPCIONES DE UI GUARDADAS PARA FUTURO:
 * 
 * Opción 1: Radio Buttons por categoría
 * - Selector único por resource/action
 * - Radio: base | pii | phi | financial | sensitive | wildcard
 * 
 * Opción 2: Checkboxes Multi-selección
 * - Permite combinar múltiples categorías
 * - Muestra campos incluidos en cada categoría
 * 
 * Opción 3: Cards con niveles (Semáforo)
 * - Visual con colores: 🟢 Base, 🟡 PII, 🟠 PHI, 🔴 Todo
 * 
 * Opción 4: Slider de sensibilidad
 * - Control deslizante de Base -> PII -> PHI -> Financial -> All
 * 
 * Opción 6: Accordion expandible
 * - Colapsa/expande por recurso
 * - Muestra categorías disponibles al expandir
 */

// Styled Components
const MatrixContainer = styled.div`
  width: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const MatrixTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const MatrixHeader = styled.thead`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
`;

const MatrixHeaderCell = styled.th`
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  
  &:last-child {
    border-right: none;
  }
`;

const MatrixRow = styled.tr<{ $expanded?: boolean }>`
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #f9fafb;
  }
  
  ${props => props.$expanded && `
    background-color: #f3f4f6;
  `}
`;

const MatrixCell = styled.td`
  padding: 10px 12px;
  font-size: 13px;
  border-right: 1px solid #e5e7eb;
  
  &:last-child {
    border-right: none;
  }
`;

const ResourceName = styled.div`
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
`;

const CategoryCheckboxGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
`;

const CategoryCheckbox = styled.label`
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
  
  &:hover {
    background: #f3f4f6;
  }
  
  input[type="checkbox"] {
    cursor: pointer;
  }
`;

const NoAccessBadge = styled.span`
  color: #6b7280;
  font-size: 12px;
  padding: 2px 8px;
  background: #f3f4f6;
  border-radius: 4px;
`;

const FieldCount = styled.span`
  color: #6b7280;
  font-size: 11px;
`;

const ActionButton = styled.button`
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
  }
`;

const ExpandedDetails = styled.tr`
  background: #f9fafb;
`;

const DetailsContainer = styled.td`
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
`;

const CategoryDetails = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
`;

const CategoryCard = styled.div<{ $selected: boolean }>`
  padding: 12px;
  border: 1px solid ${props => props.$selected ? '#6366f1' : '#e5e7eb'};
  border-radius: 6px;
  background: ${props => props.$selected ? '#eef2ff' : 'white'};
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #6366f1;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
`;

const CategoryTitle = styled.div`
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const CategoryFields = styled.div`
  font-size: 11px;
  color: #6b7280;
  line-height: 1.5;
`;

const CategoryBadge = styled.span<{ $type: string }>`
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  
  ${props => {
    switch(props.$type) {
      case 'base':
        return 'background: #dbeafe; color: #1e40af;';
      case 'pii':
        return 'background: #fef3c7; color: #92400e;';
      case 'phi':
        return 'background: #fce7f3; color: #9f1239;';
      case 'financial':
        return 'background: #dcfce7; color: #166534;';
      case 'sensitive':
        return 'background: #fef2f2; color: #991b1b;';
      case 'wildcard':
        return 'background: #e9d5ff; color: #6b21a8;';
      default:
        return 'background: #f3f4f6; color: #374151;';
    }
  }}
`;

// Component Props
interface Permission {
  resource: string;
  action: string;
  category: string;
  permission_id: string;
  available_fields: string[];
}

interface PermissionsMatrixProps {
  permissions: Permission[];
  selectedPermissions: Map<string, Set<string>>; // resource.action -> Set of categories
  onPermissionChange: (resource: string, action: string, categories: Set<string>) => void;
  onRLSClick?: (resource: string, action: string) => void;
}

const PermissionsMatrix: React.FC<PermissionsMatrixProps> = ({
  permissions,
  selectedPermissions,
  onPermissionChange,
  onRLSClick
}) => {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  
  // Group permissions by resource and action
  const groupedPermissions = React.useMemo(() => {
    const grouped = new Map<string, Map<string, Permission[]>>();
    
    permissions.forEach(perm => {
      if (!grouped.has(perm.resource)) {
        grouped.set(perm.resource, new Map());
      }
      const resourceMap = grouped.get(perm.resource)!;
      
      if (!resourceMap.has(perm.action)) {
        resourceMap.set(perm.action, []);
      }
      resourceMap.get(perm.action)!.push(perm);
    });
    
    return grouped;
  }, [permissions]);
  
  const toggleExpanded = (resource: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(resource)) {
      newExpanded.delete(resource);
    } else {
      newExpanded.add(resource);
    }
    setExpandedRows(newExpanded);
  };
  
  const getSelectedCategories = (resource: string, action: string): Set<string> => {
    return selectedPermissions.get(`${resource}.${action}`) || new Set();
  };
  
  const isCategorySelected = (resource: string, action: string, category: string): boolean => {
    const selected = getSelectedCategories(resource, action);
    return selected.has(category);
  };
  
  const handleCategoryToggle = (resource: string, action: string, category: string) => {
    const currentCategories = new Set(getSelectedCategories(resource, action));
    
    if (currentCategories.has(category)) {
      currentCategories.delete(category);
    } else {
      currentCategories.add(category);
    }
    
    onPermissionChange(resource, action, currentCategories);
  };
  
  const getFieldCount = (resource: string, action: string, category: string): number => {
    const resourceMap = groupedPermissions.get(resource);
    if (!resourceMap) return 0;
    
    const actionPerms = resourceMap.get(action);
    if (!actionPerms) return 0;
    
    const categoryPerm = actionPerms.find(p => p.category === category);
    return categoryPerm ? categoryPerm.available_fields.length : 0;
  };
  
  const getCategoryIcon = (category: string) => {
    switch(category) {
      case 'base': return '🔵';
      case 'pii': return '🟡';
      case 'phi': return '🟠';
      case 'financial': return '💰';
      case 'sensitive': return '🔴';
      case 'wildcard': return '⭐';
      default: return '⚪';
    }
  };
  
  return (
    <MatrixContainer>
      <MatrixTable>
        <MatrixHeader>
          <tr>
            <MatrixHeaderCell style={{ width: '15%' }}>Resource</MatrixHeaderCell>
            <MatrixHeaderCell style={{ width: '20%' }}>Read</MatrixHeaderCell>
            <MatrixHeaderCell style={{ width: '20%' }}>Write</MatrixHeaderCell>
            <MatrixHeaderCell style={{ width: '20%' }}>Delete</MatrixHeaderCell>
            <MatrixHeaderCell style={{ width: '10%' }}>Fields</MatrixHeaderCell>
            <MatrixHeaderCell style={{ width: '15%' }}>Actions</MatrixHeaderCell>
          </tr>
        </MatrixHeader>
        <tbody>
          {Array.from(groupedPermissions.entries()).map(([resource, actionMap]) => {
            const isExpanded = expandedRows.has(resource);
            const actions = ['read', 'write', 'delete'];
            
            return (
              <React.Fragment key={resource}>
                <MatrixRow $expanded={isExpanded}>
                  <MatrixCell>
                    <ResourceName onClick={() => toggleExpanded(resource)}>
                      <i className={`fas ${isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}`} style={{fontSize: '16px'}}></i>
                      <span>{resource}</span>
                    </ResourceName>
                  </MatrixCell>
                  
                  {actions.map(action => {
                    const actionPerms = actionMap.get(action) || [];
                    
                    return (
                      <MatrixCell key={action}>
                        {actionPerms.length > 0 ? (
                          <CategoryCheckboxGroup>
                            {actionPerms.map(perm => (
                              <CategoryCheckbox key={perm.category}>
                                <input
                                  type="checkbox"
                                  checked={isCategorySelected(resource, action, perm.category)}
                                  onChange={() => handleCategoryToggle(resource, action, perm.category)}
                                />
                                <span>{getCategoryIcon(perm.category)} {perm.category}</span>
                              </CategoryCheckbox>
                            ))}
                          </CategoryCheckboxGroup>
                        ) : (
                          <NoAccessBadge>N/A</NoAccessBadge>
                        )}
                      </MatrixCell>
                    );
                  })}
                  
                  <MatrixCell>
                    <FieldCount>
                      {Array.from(actionMap.values()).reduce((acc, perms) => {
                        const selectedCats = selectedPermissions.get(`${resource}.${perms[0]?.action}`);
                        if (!selectedCats) return acc;
                        
                        // Get unique fields from all selected categories
                        const allFields = new Set<string>();
                        perms.forEach(p => {
                          if (selectedCats.has(p.category)) {
                            p.available_fields.forEach(f => allFields.add(f));
                          }
                        });
                        return acc + allFields.size;
                      }, 0)} fields selected
                    </FieldCount>
                  </MatrixCell>
                  
                  <MatrixCell>
                    <ActionButton onClick={() => toggleExpanded(resource)}>
                      {isExpanded ? 'Hide' : 'Details'}
                    </ActionButton>
                    {onRLSClick && (
                      <ActionButton 
                        onClick={() => onRLSClick(resource, 'all')}
                        style={{ marginLeft: '4px' }}
                      >
                        <i className="fas fa-database" style={{fontSize: '12px', display: 'inline'}}></i> RLS
                      </ActionButton>
                    )}
                  </MatrixCell>
                </MatrixRow>
                
                {isExpanded && (
                  <ExpandedDetails>
                    <DetailsContainer colSpan={6}>
                      {actions.map(action => {
                        const actionPerms = actionMap.get(action);
                        if (!actionPerms || actionPerms.length === 0) return null;
                        
                        return (
                          <div key={action} style={{ marginBottom: '16px' }}>
                            <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#374151' }}>
                              {action.charAt(0).toUpperCase() + action.slice(1)} Permissions
                            </h4>
                            <CategoryDetails>
                              {actionPerms.map(perm => {
                                const isSelected = isCategorySelected(resource, action, perm.category);
                                
                                return (
                                  <CategoryCard
                                    key={perm.category}
                                    $selected={isSelected}
                                    onClick={() => handleCategoryToggle(resource, action, perm.category)}
                                  >
                                    <CategoryTitle>
                                      <CategoryBadge $type={perm.category}>
                                        {perm.category}
                                      </CategoryBadge>
                                      <span>({perm.available_fields.length} fields)</span>
                                    </CategoryTitle>
                                    <CategoryFields>
                                      {perm.available_fields.slice(0, 5).join(', ')}
                                      {perm.available_fields.length > 5 && `, +${perm.available_fields.length - 5} more`}
                                    </CategoryFields>
                                  </CategoryCard>
                                );
                              })}
                            </CategoryDetails>
                          </div>
                        );
                      })}
                    </DetailsContainer>
                  </ExpandedDetails>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </MatrixTable>
    </MatrixContainer>
  );
};

export default PermissionsMatrix;