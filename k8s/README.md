# MCP TreeOfThoughts - Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying MCP TreeOfThoughts in production.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingress       │    │   Service       │    │  StatefulSet    │
│   (nginx)       │───▶│   (ClusterIP)   │───▶│  (mcp-server)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   ConfigMap     │    │    Secrets      │
         └──────────────│   (config)      │    │   (jwt-keys)    │
                        │                 │    │                 │
                        └─────────────────┘    └─────────────────┘
```

## 📦 Components

### Core Resources

- **namespace.yaml**: Isolated namespace with resource quotas
- **configmap.yaml**: Application and nginx configuration
- **secrets.yaml**: JWT private keys and credentials
- **statefulset.yaml**: Main application deployment
- **service.yaml**: Service discovery and load balancing
- **rbac.yaml**: Security and permissions

### Security & Networking

- **network.yaml**: NetworkPolicy and Ingress configuration
- **autoscaling.yaml**: HPA and PodDisruptionBudget
- **monitoring.yaml**: Prometheus metrics and alerts

## 🚀 Quick Deployment

### 1. Prerequisites

```bash
# Ensure you have a Kubernetes cluster (1.24+)
kubectl version

# Install required operators (if not present)
kubectl apply -f https://github.com/prometheus-operator/prometheus-operator/releases/latest/download/bundle.yaml
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
```

### 2. Generate JWT Private Key

```bash
# Generate RSA private key
openssl genpkey -algorithm RSA -out private_key.pem

# Create base64 encoded secret
cat private_key.pem | base64 -w 0 > private_key_b64.txt

# Update secrets.yaml with the base64 encoded key
# Replace the private-key value in k8s/secrets.yaml
```

### 3. Configure Domain and TLS

Edit `k8s/network.yaml` and replace `mcp-api.yourdomain.com` with your actual domain:

```yaml
spec:
  tls:
    - hosts:
        - your-domain.com # Replace this
      secretName: mcp-tls-secret
  rules:
    - host: your-domain.com # Replace this
```

### 4. Deploy to Kubernetes

```bash
# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/statefulset.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/network.yaml
kubectl apply -f k8s/autoscaling.yaml
kubectl apply -f k8s/monitoring.yaml
```

### 5. Verify Deployment

```bash
# Check pod status
kubectl get pods -n mcp-treeofthoughts

# Check services
kubectl get svc -n mcp-treeofthoughts

# Check ingress
kubectl get ingress -n mcp-treeofthoughts

# View logs
kubectl logs -n mcp-treeofthoughts -l app=mcp-treeofthoughts -f
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `configmap.yaml`:

| Variable               | Default | Description                    |
| ---------------------- | ------- | ------------------------------ |
| `JWT_ALGORITHM`        | RS256   | JWT signing algorithm          |
| `JWT_EXPIRATION_HOURS` | 24      | Token validity period          |
| `KEY_ROTATION_HOURS`   | 168     | Key rotation interval (7 days) |
| `KEY_OVERLAP_HOURS`    | 24      | Grace period for old keys      |
| `JWKS_CACHE_MAX_AGE`   | 3600    | JWKS endpoint cache duration   |
| `MAX_THOUGHTS_DEPTH`   | 5       | Tree of Thoughts max depth     |
| `EVALUATION_STRATEGY`  | hybrid  | Evaluation strategy            |

### Security Features

- **Non-root containers**: Running as user 1001
- **Read-only filesystem**: Prevents runtime modifications
- **Resource limits**: CPU and memory constraints
- **Network policies**: Restricted ingress/egress
- **RBAC**: Minimal required permissions
- **Secret management**: Encrypted key storage

### Scaling Configuration

- **Initial replicas**: 1
- **Max replicas**: 5
- **CPU target**: 70%
- **Memory target**: 80%
- **Scale-down stabilization**: 5 minutes
- **Scale-up stabilization**: 30 seconds

## 📊 Monitoring

### Metrics Endpoints

- **Health**: `http://mcp-api.yourdomain.com/health`
- **JWKS**: `http://mcp-api.yourdomain.com/.well-known/jwks.json`
- **Metrics**: Internal port 8080 (Prometheus format)

### Key Alerts

- **MCPServerDown**: Server unavailable > 1 minute
- **MCPHighCPUUsage**: CPU > 80% for 5 minutes
- **MCPHighMemoryUsage**: Memory > 90% for 5 minutes
- **MCPJWTKeyRotationDue**: Key age > 7 days
- **MCPHighErrorRate**: 5xx errors > 10% for 2 minutes

### Prometheus Queries

```promql
# Request rate
rate(mcp_http_requests_total[5m])

# Error rate
rate(mcp_http_requests_total{status=~"5.."}[5m]) / rate(mcp_http_requests_total[5m])

# JWT key age
time() - mcp_jwt_key_created_timestamp

# Resource utilization
rate(container_cpu_usage_seconds_total{pod=~"mcp-treeofthoughts-.*"}[5m])
```

## 🔐 Security Best Practices

### 1. Key Management

```bash
# Rotate JWT keys regularly
kubectl create secret generic mcp-treeofthoughts-secrets-new \
  --from-file=private-key=new_private_key.pem \
  -n mcp-treeofthoughts

# Update StatefulSet to use new secret
kubectl patch statefulset mcp-treeofthoughts \
  -n mcp-treeofthoughts \
  --patch='{"spec":{"template":{"spec":{"volumes":[{"name":"private-key","secret":{"secretName":"mcp-treeofthoughts-secrets-new"}}]}}}}'
```

### 2. Network Security

- **TLS termination**: At ingress level
- **Internal communication**: Service mesh (Istio recommended)
- **Network policies**: Deny-by-default with explicit allows
- **Rate limiting**: 100 requests/minute per IP

### 3. Container Security

- **Image scanning**: Implement in CI/CD pipeline
- **Vulnerability management**: Regular base image updates
- **Runtime security**: Consider tools like Falco
- **Admission controllers**: OPA Gatekeeper for policy enforcement

## 🚨 Troubleshooting

### Common Issues

#### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -n mcp-treeofthoughts -l app=mcp-treeofthoughts

# Check logs
kubectl logs -n mcp-treeofthoughts -l app=mcp-treeofthoughts --previous
```

#### JWKS Endpoint Not Accessible

```bash
# Test internal connectivity
kubectl run debug --rm -it --image=curlimages/curl -- \
  curl -v http://mcp-treeofthoughts-service.mcp-treeofthoughts.svc.cluster.local/.well-known/jwks.json

# Check ingress
kubectl get ingress -n mcp-treeofthoughts -o yaml
```

#### Key Rotation Issues

```bash
# Check current key timestamp
kubectl exec -n mcp-treeofthoughts deployment/mcp-treeofthoughts -- \
  cat /data/jwt_key_timestamp

# Manual key rotation
kubectl delete pod -n mcp-treeofthoughts -l app=mcp-treeofthoughts
```

### Performance Tuning

#### High CPU Usage

```bash
# Increase CPU limits
kubectl patch statefulset mcp-treeofthoughts -n mcp-treeofthoughts --patch='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "mcp-server",
          "resources": {
            "limits": {"cpu": "2000m"},
            "requests": {"cpu": "500m"}
          }
        }]
      }
    }
  }
}'
```

#### Memory Issues

```bash
# Increase memory limits
kubectl patch statefulset mcp-treeofthoughts -n mcp-treeofthoughts --patch='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "mcp-server",
          "resources": {
            "limits": {"memory": "4Gi"},
            "requests": {"memory": "1Gi"}
          }
        }]
      }
    }
  }
}'
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [JWKS Specification](https://datatracker.ietf.org/doc/html/rfc7517)
- [Prometheus Monitoring](https://prometheus.io/docs/)

## 🤝 Support

For production deployment support:

1. **Documentation Issues**: Update this README
2. **Configuration Problems**: Check ConfigMap values
3. **Security Concerns**: Review RBAC and NetworkPolicies
4. **Performance Issues**: Analyze metrics and adjust resources
5. **Key Management**: Follow rotation procedures

---

**Production Readiness Checklist:**

- [ ] Private keys generated and stored securely
- [ ] Domain configured with valid TLS certificate
- [ ] Resource limits appropriate for workload
- [ ] Monitoring and alerting configured
- [ ] Backup and disaster recovery plan
- [ ] Security scanning in CI/CD pipeline
- [ ] Documentation updated for your environment
