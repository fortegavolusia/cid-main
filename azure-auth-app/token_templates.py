"""
Token Template Management for CIDS
Applies custom token structures based on AD group membership
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TokenTemplateManager:
    """Manages token templates and applies them based on AD groups"""
    
    def __init__(self, templates_file: str = "token_templates.json"):
        self.templates_file = templates_file
        self.templates: List[Dict] = []
        self.load_templates()
    
    def load_templates(self):
        """Load templates from storage"""
        try:
            with open(self.templates_file, 'r') as f:
                data = json.load(f)
                self.templates = data.get('templates', [])
                logger.info(f"Loaded {len(self.templates)} token templates")
        except FileNotFoundError:
            logger.info("No templates file found, using defaults")
            self.templates = self.get_default_templates()
            self.save_templates()
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self.templates = []
    
    def save_templates(self):
        """Save templates to storage"""
        try:
            data = {
                'templates': self.templates,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.templates_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.templates)} templates")
        except Exception as e:
            logger.error(f"Error saving templates: {e}")
    
    def get_default_templates(self) -> List[Dict]:
        """Get default token templates"""
        return [
            {
                'name': 'Default Token',
                'description': 'Standard token for all users when no group-specific template matches',
                'adGroups': [],  # Empty means it applies as fallback
                'priority': 0,
                'enabled': True,
                'claims': [
                    {'key': 'iss', 'include': True},
                    {'key': 'sub', 'include': True},
                    {'key': 'aud', 'include': True},
                    {'key': 'exp', 'include': True},
                    {'key': 'iat', 'include': True},
                    {'key': 'email', 'include': True},
                    {'key': 'name', 'include': True},
                ]
            }
        ]
    
    def find_matching_template(self, user_groups: List[str]) -> Optional[Dict]:
        """
        Find the best matching template based on user's AD groups
        
        Args:
            user_groups: List of AD groups the user belongs to
            
        Returns:
            Matching template or None
        """
        # Filter enabled templates
        enabled_templates = [t for t in self.templates if t.get('enabled', True)]
        
        # Separate templates into group-specific and default
        group_templates = []
        default_template = None
        
        for template in enabled_templates:
            template_groups = template.get('adGroups', [])
            
            # If template has no groups, it's a default/fallback
            if not template_groups:
                # Keep track of the default template (use highest priority if multiple)
                if default_template is None or template.get('priority', 0) > default_template.get('priority', 0):
                    default_template = template
                continue
            
            # Check if user has any of the template's groups
            for group in template_groups:
                if group in user_groups:
                    group_templates.append((template, template.get('priority', 0)))
                    break
        
        # If we have group-specific matches, use the highest priority one
        if group_templates:
            # Sort by priority (highest first)
            group_templates.sort(key=lambda x: x[1], reverse=True)
            selected = group_templates[0][0]
            logger.info(f"Selected group-specific template: {selected['name']} (priority: {selected.get('priority', 0)})")
            return selected
        
        # Otherwise fall back to default template
        if default_template:
            logger.info(f"Using default template: {default_template['name']}")
            return default_template
        
        logger.info("No matching template found")
        return None
    
    def apply_template(self, token_data: Dict, user_groups: List[str]) -> Dict:
        """
        Apply the appropriate template to token data based on user's groups
        
        Args:
            token_data: Original token data
            user_groups: User's AD groups
            
        Returns:
            Modified token data based on template
        """
        logger.info(f"Applying template for user with groups: {user_groups}")
        logger.info(f"Available templates: {[t['name'] for t in self.templates if t.get('enabled', True)]}")
        
        template = self.find_matching_template(user_groups)
        
        if not template:
            logger.info("No matching template found, using all claims")
            return token_data
        
        logger.info(f"Applying template: {template['name']} (has groups: {template.get('adGroups', [])})")
        
        # Build new token with template-defined claims
        filtered_token = {}
        template_claims = {c['key']: c for c in template.get('claims', [])}
        
        # Always include required JWT claims
        required_claims = ['iss', 'sub', 'aud', 'exp', 'iat', 'nbf', 'jti', 'token_type', 'token_version']
        
        # First, add all claims defined in the template
        for claim in template.get('claims', []):
            key = claim.get('key')
            if not key:
                continue
                
            # Check if this claim exists in the original token data
            if key in token_data:
                # Use the value from the original token
                filtered_token[key] = token_data[key]
            elif claim.get('value') is not None:
                # Use the default value from the template if specified
                filtered_token[key] = claim.get('value')
            elif claim.get('type') == 'array':
                # Initialize empty array for array types if not present
                filtered_token[key] = []
            elif claim.get('type') == 'object':
                # Initialize empty object for object types if not present
                filtered_token[key] = {}
            # For other types without values, only include if in original token
        
        # Ensure all required JWT claims are present
        for key in required_claims:
            if key in token_data and key not in filtered_token:
                filtered_token[key] = token_data[key]
        
        # Add any additional required fields from original token
        # that might not be in the template but are essential
        if 'email' in token_data and 'email' not in filtered_token:
            filtered_token['email'] = token_data['email']
        if 'name' in token_data and 'name' not in filtered_token:
            filtered_token['name'] = token_data['name']
        
        # Add template metadata
        filtered_token['_template_applied'] = template['name']
        filtered_token['_template_priority'] = template.get('priority', 0)
        
        return filtered_token
    
    def update_template(self, template_name: str, template_data: Dict) -> bool:
        """
        Update or add a template
        
        Args:
            template_name: Name of the template
            template_data: Template configuration
            
        Returns:
            Success status
        """
        try:
            # Find existing template
            existing_index = next(
                (i for i, t in enumerate(self.templates) if t['name'] == template_name),
                None
            )
            
            if existing_index is not None:
                self.templates[existing_index] = template_data
            else:
                self.templates.append(template_data)
            
            self.save_templates()
            return True
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """
        Delete a template
        
        Args:
            template_name: Name of the template to delete
            
        Returns:
            Success status
        """
        try:
            self.templates = [t for t in self.templates if t['name'] != template_name]
            self.save_templates()
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False
    
    def get_all_templates(self) -> List[Dict]:
        """Get all templates"""
        return self.templates
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get a specific template by name"""
        return next((t for t in self.templates if t['name'] == template_name), None)