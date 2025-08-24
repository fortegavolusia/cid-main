#!/usr/bin/env python3
"""
Script to add the 'single test' template to the backend
"""
import json

# Load existing templates
with open('/home/jnbailey/Desktop/CIDS/azure-auth-app/token_templates.json', 'r') as f:
    data = json.load(f)

# Add the 'single test' template
single_test_template = {
    "name": "single test",
    "description": "Test template for Information Technology Division",
    "adGroups": [
        "Information Technology Division"
    ],
    "priority": 15,  # Higher priority than default (0) and developer (5) but lower than admin (10)
    "enabled": True,
    "claims": [
        {"key": "iss", "include": True},
        {"key": "sub", "include": True},
        {"key": "aud", "include": True},
        {"key": "exp", "include": True},
        {"key": "iat", "include": True},
        {"key": "email", "include": True},
        {"key": "name", "include": True},
        {"key": "roles", "include": True}
    ]
}

# Check if template already exists
template_exists = any(t['name'] == 'single test' for t in data['templates'])

if not template_exists:
    data['templates'].append(single_test_template)
    print("Added 'single test' template")
else:
    # Update existing template
    for i, t in enumerate(data['templates']):
        if t['name'] == 'single test':
            data['templates'][i] = single_test_template
            print("Updated 'single test' template")
            break

# Save back to file
with open('/home/jnbailey/Desktop/CIDS/azure-auth-app/token_templates.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Template synced successfully!")
print(f"Total templates: {len(data['templates'])}")