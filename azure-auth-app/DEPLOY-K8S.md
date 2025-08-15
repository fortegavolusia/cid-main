# Deploying CIDS Auth to Kubernetes (RKE2)

This guide covers deploying the CIDS authentication service to RKE2 or any Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (RKE2 or compatible)
- `kubectl` configured to access your cluster
- GitHub Container Registry access token
- SSL certificates (or cert-manager installed)

## Quick Deploy Steps

### 1. Build and Push to GHCR

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Build and push the image
docker build -t ghcr.io/jnbaileyiv-cto/cids-2:v2.0.0 .
docker push ghcr.io/jnbaileyiv-cto/cids-2:v2.0.0

# Also tag as latest
docker tag ghcr.io/jnbaileyiv-cto/cids-2:v2.0.0 ghcr.io/jnbaileyiv-cto/cids-2:latest
docker push ghcr.io/jnbaileyiv-cto/cids-2:latest
```

### 2. Configure Secrets

First, create your configuration files:

```bash
# Copy and edit the secrets
cp k8s/secret.yaml k8s/secret.local.yaml

# Edit k8s/secret.local.yaml with your actual values:
# - AZURE_CLIENT_ID
# - AZURE_CLIENT_SECRET
# - AZURE_TENANT_ID
# - ADMIN_EMAILS
# - Generate SECRET_KEY: openssl rand -base64 32
```

### 3. Generate TLS Certificate

For internal service communication:

```bash
# Generate self-signed cert for the service
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=cids-auth.cids-auth.svc.cluster.local"

# Create the secret
kubectl create secret tls cids-auth-tls \
  --cert=tls.crt \
  --key=tls.key \
  -n cids-auth --dry-run=client -o yaml > k8s/certificate-generated.yaml
```

### 4. Deploy to Kubernetes

```bash
# Apply all resources
kubectl apply -k k8s/

# Or apply individually:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.local.yaml  # Your edited secrets
kubectl apply -f k8s/certificate-generated.yaml  # Generated cert
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### 5. Verify Deployment

```bash
# Check pods are running
kubectl get pods -n cids-auth

# Check service
kubectl get svc -n cids-auth

# Check ingress
kubectl get ingress -n cids-auth

# View logs
kubectl logs -n cids-auth -l app.kubernetes.io/name=cids-auth

# Test health endpoint (from inside cluster)
kubectl run -n cids-auth test-curl --image=curlimages/curl:latest --rm -it -- \
  curl -k https://cids-auth:443/health
```

## Production Considerations

### 1. High Availability

- The deployment runs 2 replicas by default
- For production, consider:
  - Anti-affinity rules to spread pods across nodes
  - Increase replicas based on load
  - Use HPA (Horizontal Pod Autoscaler)

### 2. Storage

- Currently uses local PVC for app data
- For production, consider:
  - Shared storage (NFS, Ceph, etc.) for multi-replica access
  - PostgreSQL for data persistence
  - Redis for session storage

### 3. TLS/SSL

- Update ingress with your domain
- Use cert-manager for automatic certificate management:

```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

### 4. Monitoring

Add Prometheus annotations to the deployment:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### 5. Network Policies

Create network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cids-auth-netpol
  namespace: cids-auth
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: cids-auth
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # For Azure AD
    - protocol: TCP
      port: 53   # DNS
```

## Updating the Application

To update to a new version:

```bash
# Build and push new version
docker build -t ghcr.io/jnbaileyiv-cto/cids-2:v2.1.0 .
docker push ghcr.io/jnbaileyiv-cto/cids-2:v2.1.0

# Update deployment
kubectl set image deployment/cids-auth \
  cids-auth=ghcr.io/jnbaileyiv-cto/cids-2:v2.1.0 \
  -n cids-auth

# Or edit kustomization.yaml and reapply
kubectl apply -k k8s/
```

## Troubleshooting

### Pod not starting

```bash
# Check pod events
kubectl describe pod -n cids-auth <pod-name>

# Check logs
kubectl logs -n cids-auth <pod-name> --previous
```

### Certificate issues

```bash
# Verify certificate is mounted
kubectl exec -n cids-auth <pod-name> -- ls -la /app/certs/

# Check certificate details
kubectl exec -n cids-auth <pod-name> -- openssl x509 -in /app/certs/cert.pem -text -noout
```

### Storage issues

```bash
# Check PVC status
kubectl get pvc -n cids-auth

# Check if data is persisted
kubectl exec -n cids-auth <pod-name> -- ls -la /app/app_data/
```

## Backup and Restore

### Backup app data

```bash
# Create backup job
kubectl create job -n cids-auth backup-$(date +%Y%m%d) --from=cronjob/backup-job
```

### Restore from backup

```bash
# Copy backup data to PVC
kubectl cp backup.tar.gz cids-auth/<pod-name>:/app/app_data/
kubectl exec -n cids-auth <pod-name> -- tar -xzf /app/app_data/backup.tar.gz -C /app/app_data/
```