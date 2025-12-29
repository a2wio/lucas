# Clopus Watcher

A Kubernetes-native Claude Code watcher that monitors pods, detects errors, and applies hotfixes directly, or just writes a report on its findings.

## Overview

Clopus Watcher runs as a CronJob that:

1. Monitors pods in a target namespace
2. Detects degraded pods (CrashLoopBackOff, Error, etc.)
3. Reads logs to understand the error
4. Execs into the pod, explores and applies a hotfix
5. Records the fix to SQLite & provides a report

A separate Dashboard deployment provides a web UI to view all detected errors and applied fixes.

## Prerequisites

**Cluster:**

- Kubernetes cluster
- Sealed Secrets (for API key / Claude Code Credentials file)

**Local (to build the images):**

- podman / docker / etc.
- kubectl
- container registry access

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TARGET_NAMESPACE` | Namespace to monitor | `default` |
| `AUTH_MODE` | Auth method: `api-key` or `credentials` | `api-key` |
| `WATCHER_MODE` | Watcher mode: `autonomous` or `watcher` | `autonomous` |
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

## Continuous Integration

### Release Images Workflow

- File: `.github/workflows/build-and-push.yaml`
- Trigger: any Git tag push or manual `workflow_dispatch`
- Action: builds both Dockerfiles with Buildx and publishes `clopus-watcher-dashboard` and `clopus-watcher` images to `ghcr.io/<owner>` using the tag name plus a `latest` tag.

### PR Dockerfile Tests

- File: `.github/workflows/pr-docker-tests.yaml`
- Trigger: pull requests that target `main` (after maintainers approve the run) or manual `workflow_dispatch`
- Action: rebuilds both Dockerfiles to validate they stay healthy; the job targets the `pr-docker-tests` environment so you can require owner review under *Settings → Environments* to stop untrusted forks from auto-consuming minutes.
