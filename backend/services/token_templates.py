"""Token Template Management for CIDS (migrated)"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backend.utils.paths import data_path, config_path

logger = logging.getLogger(__name__)


class TokenTemplateManager:
    def __init__(self, templates_file: str = None):
        new_path = str(data_path("token_templates.json"))
        old_path = str(config_path("token_templates.json"))
        self.templates_file = templates_file or new_path
        self.templates: List[Dict] = []
        self._migrate_old_location(old_path, new_path)
        self.load_templates()
    def _migrate_old_location(self, old_path: str, new_path: str):
        try:
            if os.path.exists(old_path) and not os.path.exists(new_path):
                # Ensure target directory exists
                Path(new_path).parent.mkdir(parents=True, exist_ok=True)
                with open(old_path, 'r') as f:
                    data = f.read()
                with open(new_path, 'w') as f:
                    f.write(data)
                logger.info(f"Migrated token templates from {old_path} to {new_path}")
        except Exception as e:
            logger.error(f"Failed to migrate token_templates.json: {e}")


    def load_templates(self):
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
        try:
            p = Path(self.templates_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {'templates': self.templates, 'updated_at': datetime.now().isoformat()}
            with open(p, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.templates)} templates")
        except Exception as e:
            logger.error(f"Error saving templates: {e}")

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
        filtered_token['_template_applied'] = template['name']
        filtered_token['_template_priority'] = template.get('priority', 0)
        return filtered_token

    def update_template(self, template_name: str, template_data: Dict) -> bool:
        try:
            existing_index = next((i for i, t in enumerate(self.templates) if t['name'] == template_name), None)
            if existing_index is not None:
                self.templates[existing_index] = template_data
            else:
                self.templates.append(template_data)
            self.save_templates()
            return True
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return False


    def save_template(self, template: Dict) -> bool:
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
                return self.update_template(name, merged)
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
                return self.update_template(name, new_template)
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    def delete_template(self, template_name: str) -> bool:
        try:
            self.templates = [t for t in self.templates if t['name'] != template_name]
            self.save_templates()
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False

    def get_all_templates(self) -> List[Dict]:
        return self.templates

    def get_template(self, template_name: str) -> Optional[Dict]:
        return next((t for t in self.templates if t['name'] == template_name), None)

