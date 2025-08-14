import secrets

# Generate a secure random secret key
secret_key = secrets.token_urlsafe(32)
print(f"Your SECRET_KEY: {secret_key}")
print(f"\nAdd this to your .env file:")
print(f"SECRET_KEY={secret_key}")