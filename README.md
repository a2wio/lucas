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

| Variable | Description | Default | Required |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key | - | Yes |
| `SLACK_BOT_TOKEN` | Slack bot token (xoxb-...) | - | Yes |
| `SLACK_APP_TOKEN` | Slack app token (xapp-...) | - | Yes |
| `SRE_MODE` | `autonomous` or `watcher` | `autonomous` | No |
| `CLAUDE_MODEL` | `sonnet` or `opus` | `sonnet` | No |
| `TARGET_NAMESPACE` | Default namespace for interactive requests | `default` | No |
| `TARGET_NAMESPACES` | Comma-separated namespaces for scheduled scans | `default` | No |
| `SRE_ALERT_CHANNEL` | Channel ID for scheduled scan alerts | - | No |
| `SCAN_INTERVAL_SECONDS` | Seconds between scheduled scans | `300` | No |
| `SQLITE_PATH` | SQLite DB path | `/data/lucas.db` | No |
| `PROMPT_FILE` | System prompt path | `/app/master-prompt-interactive.md` | No |

### CronJob agent

| Variable | Description | Default | Required |
|---|---|---|---|
| `TARGET_NAMESPACE` | Namespace to scan | `default` | Yes |
| `SRE_MODE` | `autonomous` or `report` | `autonomous` | Yes |
| `AUTH_MODE` | `api-key` or `credentials` | `api-key` | Yes |
| `ANTHROPIC_API_KEY` | Claude API key (when `AUTH_MODE=api-key`) | - | Conditional |
| `credentials.json` | Mount at `/secrets/credentials.json` or `$HOME/.claude/.credentials.json` when `AUTH_MODE=credentials` | - | Conditional |
| `SLACK_WEBHOOK_URL` | Slack webhook notifications | - | No |
| `SQLITE_PATH` | SQLite DB path | `/data/lucas.db` | No |

### Dashboard

| Variable | Description | Default | Required |
|---|---|---|---|
| `SQLITE_PATH` | SQLite DB path | `/data/lucas.db` | No |
| `PORT` | HTTP port | `8080` | No |
| `LOG_PATH` | Log file path | `/data/lucas.log` | No |
| `AUTH_USER` | Dashboard login user | `a2wmin` | No |
| `AUTH_PASS` | Dashboard login password | `a2wssword` | No |

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
