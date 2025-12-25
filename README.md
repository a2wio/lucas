# Clopus Watcher

A Kubernetes-native Claude Code watcher that monitors pods, detects errors, and applies hotfixes directly.

## Overview

Clopus Watcher runs as a CronJob (every 5 minutes) that:
1. Monitors pods in a target namespace
2. Detects degraded pods (CrashLoopBackOff, Error, etc.)
3. Reads logs to understand the error
4. Execs into the pod and fixes the issue directly
5. Records the fix to SQLite

A separate Dashboard deployment provides a web UI to view all detected errors and applied fixes.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      K8s Cluster                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              clopus-watcher Namespace                   │ │
│  │                                                         │ │
│  │  ┌─────────────────────┐    ┌─────────────────────┐   │ │
│  │  │  Claude Watcher     │    │  Dashboard          │   │ │
│  │  │  (CronJob 5min)     │    │  (Deployment)       │   │ │
│  │  │  - Claude Code CLI  │    │  - Go + HTMX        │   │ │
│  │  │  - kubectl          │◄──►│  - Reads SQLite     │   │ │
│  │  └─────────────────────┘    └─────────────────────┘   │ │
│  │           │                          ▲                 │ │
│  │           │ PVC (SQLite)             │                 │ │
│  │           └──────────────────────────┘                 │ │
│  └────────────────────────────────────────────────────────┘ │
│              │                                               │
│              │ kubectl exec                                  │
│              ▼                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Target Namespace (configurable)            │ │
│  │  ┌─────┐ ┌─────┐ ┌─────┐                              │ │
│  │  │Pod A│ │Pod B│ │Pod C│  ← Claude execs in & fixes   │ │
│  │  └─────┘ └─────┘ └─────┘                              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Kubernetes cluster
- kubectl configured
- Sealed Secrets controller (for API key)
- Container registry access

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TARGET_NAMESPACE` | Namespace to monitor | `default` |
| `AUTH_MODE` | Auth method: `api-key` or `credentials` | `api-key` |
| `ANTHROPIC_API_KEY` | Claude API key (if AUTH_MODE=api-key) | - |
| `SQLITE_PATH` | Path to SQLite database | `/data/watcher.db` |

## Deployment

### Option 1: API Key (Recommended)

```bash
# 1. Create namespace
kubectl create namespace clopus-watcher

# 2. Create secret with API key
kubectl create secret generic claude-auth \
  --namespace clopus-watcher \
  --from-literal=api-key=sk-ant-xxxxx

# 3. Ensure AUTH_MODE=api-key in k8s/cronjob.yaml (default)

# 4. Deploy
./scripts/deploy.sh
```

### Option 2: Credentials File (OAuth)

```bash
# 1. Create namespace
kubectl create namespace clopus-watcher

# 2. Create secret from credentials file
kubectl create secret generic claude-credentials \
  --namespace clopus-watcher \
  --from-file=credentials.json=$HOME/.claude/.credentials.json

# 3. Edit k8s/cronjob.yaml:
#    - Set AUTH_MODE=credentials
#    - Uncomment claude-credentials volume and volumeMount

# 4. Deploy
./scripts/deploy.sh
```

## Components

### Watcher (CronJob)
- Runs every 5 minutes
- Uses Claude Code CLI to analyze and fix pods
- Writes fixes to shared SQLite database

### Dashboard (Deployment)
- Always running web UI
- Shows all detected errors and applied fixes
- Auto-updates via HTMX polling

## License

MIT - See LICENSE file
