# A2W: Lucas

A Kubernetes-native Claude Code agent that monitors pods, detects errors, and applies hotfixes directly, or just writes a report on its findings.

## Overview

A2W's Lucas agent runs as a Slack-integrated service that:
1. Responds to @mentions for on-demand Kubernetes tasks
2. Runs scheduled scans on configured namespaces
3. Detects degraded pods (CrashLoopBackOff, Error, etc.)
4. Reads logs to understand errors
5. Can exec into pods and apply hotfixes (autonomous mode)
6. Records findings to SQLite & provides reports via dashboard

A separate Dashboard deployment provides a web UI to view all detected errors, applied fixes, and token costs.

## Prerequisites

**Cluster:**

- Kubernetes cluster
- Sealed Secrets controller (for API key / Slack credentials)

**Local (to build the images):**

- podman / docker
- kubectl
- kubeseal
- Container registry access

## Environment Variables

### Agent

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | - | Yes |
| `SLACK_BOT_TOKEN` | Slack bot token (xoxb-...) | - | Yes |
| `SLACK_APP_TOKEN` | Slack app token (xapp-...) | - | Yes |
| `SRE_ALERT_CHANNEL` | Slack channel ID for scheduled scan alerts | - | No |
| `TARGET_NAMESPACE` | Primary namespace to monitor | `default` | No |
| `TARGET_NAMESPACES` | Comma-separated namespaces for scheduled scans | `default` | No |
| `LUCAS_MODE` | Agent mode: `autonomous` (can fix) or `watcher` (report only) | `autonomous` | No |
| `CLAUDE_MODEL` | Model to use: `sonnet` or `opus` | `sonnet` | No |
| `SCAN_INTERVAL_SECONDS` | Seconds between scheduled scans | `300` | No |
| `PROMPT_FILE` | Path to system prompt file | `/app/master-prompt-interactive.md` | No |
| `SQLITE_PATH` | Path to SQLite database | `/data/lucas.db` | No |

### Dashboard

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SQLITE_PATH` | Path to SQLite database (shared with agent) | `/data/lucas.db` | No |
| `PORT` | HTTP server port | `8080` | No |
| `LOG_PATH` | Path to log file | `/data/lucas.log` | No |
| `AUTH_USER` | Dashboard login username | `a2wmin` | No |
| `AUTH_PASS` | Dashboard login password | `a2wssword` | No |

## Deployment

### 1. Create Sealed Secrets

```bash
# Claude API key
kubectl create secret generic claude-auth \
  --namespace=a2w-lucas \
  --from-literal=api-key=sk-ant-xxxxx \
  --dry-run=client -o yaml | \
  kubeseal --controller-namespace sealed-secrets --controller-name sealed-secrets-controller -o yaml > claude-auth.yml

# Slack credentials
kubectl create secret generic slack-bot \
  --namespace=a2w-lucas \
  --from-literal=bot-token="xoxb-..." \
  --from-literal=app-token="xapp-..." \
  --from-literal=alert-channel="C0123456789" \
  --dry-run=client -o yaml | \
  kubeseal --controller-namespace sealed-secrets --controller-name sealed-secrets-controller -o yaml > slack-bot.yml
```

### 2. Build and Push Images

```bash
# Agent image
podman build --platform=linux/amd64 -f Dockerfile.agent -t registry.example.com/a2w/lucas:v0.1 .
podman push registry.example.com/a2w/lucas:v0.1

# Dashboard image
podman build --platform=linux/amd64 -f Dockerfile.dashboard -t registry.example.com/a2w/lucas-dashboard:v0.1 .
podman push registry.example.com/a2w/lucas-dashboard:v0.1
```

### 3. Deploy

Apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/
```

Or if using ArgoCD, the application will sync automatically.

## Modes

### Autonomous Mode (`LUCAS_MODE=autonomous`)
- Can execute commands inside pods
- Can apply hotfixes
- Full remediation capabilities

### Watcher Mode (`LUCAS_MODE=watcher`)
- Read-only access
- Reports issues without making changes
- Safe for production observation

## Models

| Model | Cost (Input/Output per 1M tokens) | Best For |
|-------|-----------------------------------|----------|
| `sonnet` | $3 / $15 | General use, cost-effective |
| `opus` | $15 / $75 | Complex debugging, thorough analysis |

## Slack Commands

Mention the bot in any channel it's invited to:

- `@lucas check pods in namespace xyz` - Health check
- `@lucas why is pod abc crashing?` - Investigate specific pod
- `@lucas show recent errors` - Review error logs
- `@lucas help` - Show available commands

Thread replies maintain conversation context for follow-up questions.

## Dashboard

Access the dashboard at `https://lucas.yourdomain.com` (or configured ingress).

**Pages:**
- **Overview** - Recent runs, pod status, error counts
- **Sessions** - Active Slack conversation sessions
- **Costs** - Token usage and cost tracking per model
- **Runbooks** - (Future) Custom remediation playbooks

**Authentication:**
Configure `AUTH_USER` and `AUTH_PASS` environment variables, or use defaults.
