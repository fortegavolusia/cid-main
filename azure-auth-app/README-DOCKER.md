# CIDS Authentication Service - Docker Deployment

This guide covers containerizing and deploying the CIDS (Centralized ID Service) authentication application.

## Quick Start

### 1. Build and Run Locally

```bash
# Build the image
docker build -t cids-auth:latest .

# Run with docker-compose
docker compose up -d

# Or run directly with Docker
docker run -d \
  --name cids-auth \
  -p 8000:8000 \
  -v $(pwd)/app_data:/app/app_data \
  -v $(pwd)/certs:/app/certs:ro \
  --env-file .env \
  cids-auth:latest
```

### 2. Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your Azure AD configuration
```

Required environment variables:
- `AZURE_CLIENT_ID`: Your Azure AD application ID
- `AZURE_CLIENT_SECRET`: Your Azure AD application secret
- `AZURE_TENANT_ID`: Your Azure AD tenant ID
- `REDIRECT_URI`: The callback URL (must match Azure AD config)
- `SECRET_KEY`: A secure random key for session encryption
- `ADMIN_EMAILS`: Comma-separated list of admin email addresses

### 3. SSL Certificates

For HTTPS support, place your certificates in the `certs/` directory:
```bash
mkdir certs
# Copy your cert.pem and key.pem files
cp /path/to/cert.pem certs/
cp /path/to/key.pem certs/
```

For local development, you can generate self-signed certificates:
```bash
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes
```

## GitHub Container Registry

### Prerequisites

1. Create a GitHub Personal Access Token with `write:packages` permission
2. Set up GitHub Actions secrets in your repository:
   - The `GITHUB_TOKEN` is automatically provided by GitHub Actions

### Manual Push

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Build and push
./build-and-push.sh v1.0.0

# Or manually:
docker build -t ghcr.io/YOUR_GITHUB_USERNAME/cids-auth:latest .
docker push ghcr.io/YOUR_GITHUB_USERNAME/cids-auth:latest
```

### Automated Builds

The GitHub Actions workflow (`.github/workflows/docker-publish.yml`) automatically:
- Builds on push to `main` or `develop` branches
- Creates multi-platform images (amd64, arm64)
- Tags images based on branch, commit SHA, and version tags
- Generates Software Bill of Materials (SBOM)

To trigger a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

## Production Deployment

### 1. Using Docker Compose

```yaml
version: '3.8'

services:
  cids-auth:
    image: ghcr.io/YOUR_GITHUB_USERNAME/cids-auth:latest
    container_name: cids-auth
    ports:
      - "443:8000"  # Map to 443 for HTTPS
    environment:
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      # ... other environment variables
    volumes:
      - ./app_data:/app/app_data
      - ./certs:/app/certs:ro
    restart: unless-stopped
```

### 2. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cids-auth
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cids-auth
  template:
    metadata:
      labels:
        app: cids-auth
    spec:
      containers:
      - name: cids-auth
        image: ghcr.io/YOUR_GITHUB_USERNAME/cids-auth:latest
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: cids-auth-secrets
              key: azure-client-id
        # ... other env vars
        volumeMounts:
        - name: app-data
          mountPath: /app/app_data
        - name: certs
          mountPath: /app/certs
          readOnly: true
      volumes:
      - name: app-data
        persistentVolumeClaim:
          claimName: cids-auth-data
      - name: certs
        secret:
          secretName: cids-auth-certs
```

## Health Checks

The container includes a health check endpoint at `/health`:
```bash
# Check health
curl -k https://localhost:8000/health
```

## Troubleshooting

1. **Container won't start**: Check logs with `docker logs cids-auth`
2. **SSL errors**: Ensure certificates are properly mounted and have correct permissions
3. **Authentication failures**: Verify Azure AD configuration and redirect URIs
4. **Permission errors**: The container runs as non-root user (UID 1000)

## Security Considerations

1. Always use HTTPS in production
2. Store sensitive environment variables securely (use Kubernetes secrets, Docker secrets, etc.)
3. Regularly update the base image and dependencies
4. Enable container scanning in your registry
5. Use read-only root filesystem where possible:
   ```bash
   docker run --read-only --tmpfs /tmp ...
   ```

## Persistence

The following directories should be persisted:
- `/app/app_data`: Application data (registered apps, etc.)
- `/app/logs`: Application logs

For production, consider using:
- PostgreSQL for application data
- Redis for session storage
- External log aggregation service