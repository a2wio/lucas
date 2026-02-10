# Deployment

This section covers the interactive Slack agent and dashboard. Choose a deployment style below.

## Options

- **ArgoCD**: point an Application at this repo and let ArgoCD sync. See `ops/deployment-argocd`.
- **Plain YAML**: apply the files with `kubectl`. See `ops/deployment-yaml`.

## Manifests

The baseline manifests live in `k8s/`:

- `namespace.yaml`
- `pvc.yaml` (creates `lucas-data` and `claude-sessions`)
- `rbac.yaml`
- `agent-deployment.yaml`
- `dashboard-deployment.yaml`
- `dashboard-service.yaml`

## Secrets

Do not apply `k8s/secret.yaml` or `k8s/slack-bot-secret.yaml` in production. They are examples only.

Recommended flow:

1. Create a sealed secret for `claude-auth` with key `api-key`.
2. Create a sealed secret for `slack-bot` with keys `bot-token`, `app-token`, and optional `alert-channel`.
3. Apply the sealed secrets.

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

## Install script

There is a helper at `scripts/install.sh` that can generate sealed secrets and manifests. It runs locally and asks for inputs. Use it if you prefer a guided setup.
