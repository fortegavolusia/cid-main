"""Token Template Management for CIDS (migrated)"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from utils.paths import data_path, config_path
from services.database import db_service

logger = logging.getLogger(__name__)


class TokenTemplateManager:
    def __init__(self, templates_file: str = None):
        # No longer using JSON file, using database instead
        self.templates: List[Dict] = []
        self.load_templates()
    # Migration method no longer needed - using database


    def load_templates(self):
        try:
            # Load from database
            db_templates = db_service.get_token_templates()
            if db_templates:
                self.templates = db_templates
                logger.info(f"Loaded {len(self.templates)} token templates from database")
            else:
                logger.info("No templates in database, using defaults")
                self.templates = self.get_default_templates()
                # Save default templates to database
                for template in self.templates:
                    db_service.save_token_template(template, user_email)
        except Exception as e:
            logger.error(f"Error loading templates from database: {e}")
            self.templates = []

    def save_templates(self, user_email: str = None):
        try:
            # Save all templates to database
            for template in self.templates:
                db_service.save_token_template(template, user_email)
            logger.info(f"Saved {len(self.templates)} templates to database")
        except Exception as e:
            logger.error(f"Error saving templates to database: {e}")

    def get_default_templates(self) -> List[Dict]:
        return [{
            'name': 'Default Token',
            'description': 'Standard token for all users when no group-specific template matches',
            'adGroups': [],
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
        }]

    def find_matching_template(self, user_groups: List[str]) -> Optional[Dict]:
        enabled_templates = [t for t in self.templates if t.get('enabled', True)]
        group_templates = []
        default_template = None
        for template in enabled_templates:
            template_groups = template.get('adGroups', [])
            if not template_groups:
                if default_template is None or template.get('priority', 0) > default_template.get('priority', 0):
                    default_template = template
                continue
            for group in template_groups:
                if group in user_groups:
                    group_templates.append((template, template.get('priority', 0)))
                    break
        if group_templates:
            group_templates.sort(key=lambda x: x[1], reverse=True)
            return group_templates[0][0]
        return default_template

    def apply_template(self, token_data: Dict, user_groups: List[str]) -> Dict:
        template = self.find_matching_template(user_groups)
        if not template:
            return token_data
        filtered_token = {}
        template_claims = {c['key']: c for c in template.get('claims', [])}
        required_claims = ['iss', 'sub', 'aud', 'exp', 'iat', 'nbf', 'jti', 'token_type', 'token_version']
        for claim in template.get('claims', []):
            key = claim.get('key')
            if not key:
                continue
            if key in token_data:
                filtered_token[key] = token_data[key]
            elif claim.get('value') is not None:
                filtered_token[key] = claim.get('value')
            elif claim.get('type') == 'array':
                filtered_token[key] = []
            elif claim.get('type') == 'object':
                filtered_token[key] = {}
        for key in required_claims:
            if key in token_data and key not in filtered_token:
                filtered_token[key] = token_data[key]
        if 'email' in token_data and 'email' not in filtered_token:
            filtered_token['email'] = token_data['email']
        if 'name' in token_data and 'name' not in filtered_token:
            filtered_token['name'] = token_data['name']

        # Always include security claims for professional token binding
        security_claims = ['bound_ip', 'bound_device']
        for key in security_claims:
            if key in token_data:
                filtered_token[key] = token_data[key]
                logger.info(f"Added security claim {key}: {token_data[key]}")
            else:
                logger.warning(f"Security claim {key} not found in token_data")

        filtered_token['_template_applied'] = template['name']
        filtered_token['_template_priority'] = template.get('priority', 0)
        return filtered_token

    def update_template(self, template_name: str, template_data: Dict, user_email: str = None) -> bool:
        try:
            existing_index = next((i for i, t in enumerate(self.templates) if t['name'] == template_name), None)
            if existing_index is not None:
                # Preserve template_id from existing template to ensure UPDATE instead of INSERT
                if 'template_id' in self.templates[existing_index]:
                    template_data['template_id'] = self.templates[existing_index]['template_id']
                self.templates[existing_index] = template_data
            else:
                self.templates.append(template_data)
            self.save_templates(user_email)
            return True
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return False


    def save_template(self, template: Dict, user_email: str = None) -> bool:
        """Save or update a token template by name.
        Merges with existing template to preserve fields like adGroups/priority/enabled
        when the client omits them.
        """
        try:
            name = template.get('name') if isinstance(template, dict) else None
            if not name:
                raise ValueError("Template must include a 'name' field")

            existing = self.get_template(name)
            if existing:
                # Merge: incoming keys overwrite existing only if provided
                merged = existing.copy()
                for k, v in template.items():
                    if v is not None:
                        merged[k] = v
                # Ensure required keys exist
                merged.setdefault('adGroups', existing.get('adGroups', []))
                merged.setdefault('priority', existing.get('priority', 0))
                merged.setdefault('enabled', existing.get('enabled', True))
                return self.update_template(name, merged, user_email)
            else:
                # Apply defaults for new templates
                new_template = {
                    'name': name,
                    'description': template.get('description'),
                    'claims': template.get('claims', []),
                    'savedAt': template.get('savedAt') or datetime.now().isoformat(),
                    'adGroups': template.get('adGroups', []),
                    'priority': template.get('priority', 0),
                    'enabled': template.get('enabled', True),
                    'isDefault': template.get('isDefault', False),
                }
                return self.update_template(name, new_template, user_email)
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    def delete_template(self, template_name: str) -> bool:
        try:
            self.templates = [t for t in self.templates if t['name'] != template_name]
            self.save_templates(user_email)
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False

    def get_all_templates(self) -> List[Dict]:
        return self.templates

    def get_template(self, template_name: str) -> Optional[Dict]:
        return next((t for t in self.templates if t['name'] == template_name), None)

