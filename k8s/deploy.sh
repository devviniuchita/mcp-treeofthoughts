#!/bin/bash

# MCP TreeOfThoughts - Kubernetes Deployment Script
# This script automates the deployment process for production environments

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="mcp-treeofthoughts"
DOMAIN="${MCP_DOMAIN:-mcp-api.example.com}"
IMAGE="${MCP_IMAGE:-mcp-treeofthoughts:latest}"
ENVIRONMENT="${MCP_ENV:-production}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Unable to connect to Kubernetes cluster."
        exit 1
    fi

    # Check openssl
    if ! command -v openssl &> /dev/null; then
        log_error "openssl not found. Please install openssl."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

generate_jwt_key() {
    log_info "Generating JWT private key..."

    local key_dir="./tmp/keys"
    mkdir -p "$key_dir"

    # Generate private key
    openssl genpkey -algorithm RSA -out "$key_dir/private_key.pem"

    # Set secure permissions
    chmod 600 "$key_dir/private_key.pem"

    # Generate base64 encoded key for Kubernetes secret
    base64 -w 0 "$key_dir/private_key.pem" > "$key_dir/private_key_b64.txt"

    log_success "JWT private key generated at $key_dir/private_key.pem"
}

update_manifests() {
    log_info "Updating Kubernetes manifests..."

    local key_b64=$(cat ./tmp/keys/private_key_b64.txt)

    # Update domain in network.yaml
    sed -i.bak "s/mcp-api\.yourdomain\.com/$DOMAIN/g" k8s/network.yaml

    # Update image in statefulset.yaml
    sed -i.bak "s|image: mcp-treeofthoughts:latest|image: $IMAGE|g" k8s/statefulset.yaml

    # Update private key in secrets.yaml
    sed -i.bak "s|private-key: LS0tLS1CRUdJTi.*|private-key: $key_b64|g" k8s/secrets.yaml

    log_success "Manifests updated for domain: $DOMAIN"
}

deploy_manifests() {
    log_info "Deploying Kubernetes manifests..."

    # Apply manifests in order
    local manifests=(
        "namespace.yaml"
        "configmap.yaml"
        "secrets.yaml"
        "rbac.yaml"
        "statefulset.yaml"
        "service.yaml"
        "network.yaml"
        "autoscaling.yaml"
        "monitoring.yaml"
    )

    for manifest in "${manifests[@]}"; do
        log_info "Applying $manifest..."
        kubectl apply -f "k8s/$manifest"
        sleep 2
    done

    log_success "All manifests deployed"
}

wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."

    # Wait for StatefulSet to be ready
    kubectl wait --for=condition=ready \
        --timeout=300s \
        statefulset/mcp-treeofthoughts \
        -n "$NAMESPACE"

    # Wait for pods to be running
    kubectl wait --for=condition=Ready \
        --timeout=300s \
        pods -l app=mcp-treeofthoughts \
        -n "$NAMESPACE"

    log_success "Deployment is ready"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Get pod status
    kubectl get pods -n "$NAMESPACE" -l app=mcp-treeofthoughts

    # Check service endpoints
    kubectl get svc -n "$NAMESPACE"

    # Check ingress
    kubectl get ingress -n "$NAMESPACE"

    # Test internal connectivity
    log_info "Testing internal health endpoint..."
    if kubectl run test-connectivity --rm -it --image=curlimages/curl --restart=Never -- \
        curl -f "http://mcp-treeofthoughts-service.$NAMESPACE.svc.cluster.local/health"; then
        log_success "Health endpoint is accessible"
    else
        log_error "Health endpoint is not accessible"
        return 1
    fi

    # Test JWKS endpoint
    log_info "Testing JWKS endpoint..."
    if kubectl run test-jwks --rm -it --image=curlimages/curl --restart=Never -- \
        curl -f "http://mcp-treeofthoughts-service.$NAMESPACE.svc.cluster.local/.well-known/jwks.json"; then
        log_success "JWKS endpoint is accessible"
    else
        log_error "JWKS endpoint is not accessible"
        return 1
    fi

    log_success "Deployment verification completed"
}

show_endpoints() {
    log_info "Deployment completed successfully!"
    echo
    echo "🌐 Service Endpoints:"
    echo "   Health Check: https://$DOMAIN/health"
    echo "   JWKS Endpoint: https://$DOMAIN/.well-known/jwks.json"
    echo "   JWT Generation: https://$DOMAIN/api/jwt"
    echo "   MCP Protocol: https://$DOMAIN/mcp/"
    echo
    echo "📊 Monitoring:"
    echo "   Metrics: kubectl port-forward -n $NAMESPACE svc/mcp-treeofthoughts-metrics 8080:8080"
    echo "   Logs: kubectl logs -n $NAMESPACE -l app=mcp-treeofthoughts -f"
    echo
    echo "🔧 Management Commands:"
    echo "   Scale up: kubectl scale statefulset mcp-treeofthoughts --replicas=3 -n $NAMESPACE"
    echo "   Update config: kubectl edit configmap mcp-treeofthoughts-config -n $NAMESPACE"
    echo "   Rotate keys: kubectl delete pod -l app=mcp-treeofthoughts -n $NAMESPACE"
    echo
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf ./tmp/keys
    rm -f k8s/*.bak
}

rollback() {
    log_warning "Rolling back deployment..."

    # Restore backup manifests
    if [ -f k8s/network.yaml.bak ]; then
        mv k8s/network.yaml.bak k8s/network.yaml
    fi
    if [ -f k8s/statefulset.yaml.bak ]; then
        mv k8s/statefulset.yaml.bak k8s/statefulset.yaml
    fi
    if [ -f k8s/secrets.yaml.bak ]; then
        mv k8s/secrets.yaml.bak k8s/secrets.yaml
    fi

    # Delete namespace (this removes all resources)
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

    cleanup
    log_warning "Rollback completed"
}

# Help function
show_help() {
    cat << EOF
MCP TreeOfThoughts Kubernetes Deployment Script

Usage: $0 [OPTIONS]

Options:
    -d, --domain DOMAIN     Set the deployment domain (default: mcp-api.example.com)
    -i, --image IMAGE       Set the container image (default: mcp-treeofthoughts:latest)
    -e, --env ENVIRONMENT   Set environment (default: production)
    -c, --check-only        Only check prerequisites
    -r, --rollback          Rollback deployment
    -h, --help              Show this help

Environment Variables:
    MCP_DOMAIN              Deployment domain
    MCP_IMAGE               Container image
    MCP_ENV                 Environment name

Examples:
    $0 --domain mcp-api.mycompany.com --image myregistry/mcp:v1.0.0
    $0 --check-only
    $0 --rollback

EOF
}

# Main function
main() {
    local check_only=false
    local do_rollback=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -i|--image)
                IMAGE="$2"
                shift 2
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -c|--check-only)
                check_only=true
                shift
                ;;
            -r|--rollback)
                do_rollback=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Execute based on mode
    if [[ "$do_rollback" == true ]]; then
        rollback
        exit 0
    fi

    check_prerequisites

    if [[ "$check_only" == true ]]; then
        log_success "Prerequisites check completed"
        exit 0
    fi

    # Trap to cleanup on exit
    trap cleanup EXIT
    trap rollback ERR

    log_info "Starting MCP TreeOfThoughts deployment..."
    log_info "Domain: $DOMAIN"
    log_info "Image: $IMAGE"
    log_info "Environment: $ENVIRONMENT"

    generate_jwt_key
    update_manifests
    deploy_manifests
    wait_for_deployment
    verify_deployment
    show_endpoints

    log_success "MCP TreeOfThoughts deployed successfully! 🎉"
}

# Run main function
main "$@"
