#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$SCRIPT_DIR/../k8s"

echo "=== Deploying Clopus Watcher ==="

# Apply in order
echo "Creating namespace..."
kubectl apply -f "$K8S_DIR/namespace.yaml"

echo "Creating RBAC..."
kubectl apply -f "$K8S_DIR/rbac.yaml"

echo "Creating secrets..."
kubectl apply -f "$K8S_DIR/sealed-secret.yaml"

echo "Creating config..."
kubectl apply -f "$K8S_DIR/configmap.yaml"

echo "Creating persistent volume..."
kubectl apply -f "$K8S_DIR/pvc.yaml"

echo "Creating dashboard..."
kubectl apply -f "$K8S_DIR/dashboard-deployment.yaml"
kubectl apply -f "$K8S_DIR/dashboard-service.yaml"

echo "Creating watcher cronjob..."
kubectl apply -f "$K8S_DIR/cronjob.yaml"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Dashboard: kubectl port-forward -n clopus-watcher svc/dashboard 8080:80"
echo "Logs: kubectl logs -n clopus-watcher -l app=dashboard"
echo "CronJob: kubectl get cronjobs -n clopus-watcher"
