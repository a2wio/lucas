# Plain YAML

Use `kubectl apply` to deploy the manifests in `k8s/`.

## Secrets

Create secrets before applying the deployments. Example flow using sealed secrets:

1. Seal `claude-auth` with key `api-key`.
2. Seal `slack-bot` with keys `bot-token`, `app-token`, and optional `alert-channel`.

## Apply

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/agent-deployment.yaml
kubectl apply -f k8s/dashboard-deployment.yaml
kubectl apply -f k8s/dashboard-service.yaml
```

## Access the dashboard

```bash
kubectl -n a2w-lucas port-forward svc/dashboard 8080:80
```

Open `http://localhost:8080`.
