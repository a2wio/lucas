# A2W: Lucas

A Kubernetes operations and reliability agent. It runs in-cluster, inspects pods and logs, can report or remediate issues based on mode, and exposes a dashboard backed by SQLite.

## What it does

- Slack-first investigations with thread context.
- Scheduled scans across namespaces.
- Optional remediation when allowed.
- Dashboard for runs, sessions, and token usage.

## Modes

Interactive agent (`Dockerfile.agent`):

- `SRE_MODE=autonomous`: can fix issues.
- `SRE_MODE=watcher`: report-only.

CronJob agent (`Dockerfile.lucas`):

- `SRE_MODE=autonomous`: can fix issues.
- `SRE_MODE=report`: report-only.

## Environment variables

### Interactive agent

Required:

- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`

Common:

- `SRE_MODE` (`autonomous` or `watcher`)
- `CLAUDE_MODEL` (`sonnet` or `opus`)
- `TARGET_NAMESPACE`
- `TARGET_NAMESPACES` (comma-separated)
- `SRE_ALERT_CHANNEL` (enables scheduled scans)
- `SCAN_INTERVAL_SECONDS`
- `SQLITE_PATH` (default `/data/lucas.db`)
- `PROMPT_FILE` (default `/app/master-prompt-interactive.md`)

### CronJob agent

Required:

- `TARGET_NAMESPACE`
- `SRE_MODE` (`autonomous` or `report`)
- `AUTH_MODE` (`api-key` or `credentials`)

If `AUTH_MODE=api-key`:

- `ANTHROPIC_API_KEY`

If `AUTH_MODE=credentials`:

- Mount `credentials.json` at `/secrets/credentials.json` or `$HOME/.claude/.credentials.json`.

Optional:

- `SLACK_WEBHOOK_URL` (Slack notifications)
- `SQLITE_PATH` (default `/data/lucas.db`)

### Dashboard

- `SQLITE_PATH` (default `/data/lucas.db`)
- `PORT` (default `8080`)
- `LOG_PATH` (default `/data/lucas.log`)
- `AUTH_USER` (default `a2wmin`)
- `AUTH_PASS` (default `a2wssword`)

## Deployment (interactive agent + dashboard)

1. Create sealed secrets for `claude-auth` and `slack-bot`.
2. Build and push images.
3. Apply the manifests.

Do not apply `k8s/secret.yaml` or `k8s/slack-bot-secret.yaml` in production. They are examples only.

Apply the manifests explicitly:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/agent-deployment.yaml
kubectl apply -f k8s/dashboard-deployment.yaml
kubectl apply -f k8s/dashboard-service.yaml
```

Port-forward the dashboard:

```bash
kubectl -n a2w-lucas port-forward svc/dashboard 8080:80
```

Open `http://localhost:8080`.

## CronJob mode

Use `k8s/cronjob.yaml`. It runs a batch scan on a schedule and writes to SQLite. It can notify Slack via webhook.

## Slack commands

- `@lucas check pods in namespace xyz`
- `@lucas why is pod abc crashing?`
- `@lucas show recent errors`
- `@lucas help`

## Dashboard

The dashboard shows recent runs, sessions, costs, and runbooks. Configure login with `AUTH_USER` and `AUTH_PASS`.

## Notes

- The helper script at `scripts/install.sh` can generate manifests and sealed secrets.
- Docs live in `docs/` (VitePress).
