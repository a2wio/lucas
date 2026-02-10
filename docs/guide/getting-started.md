# Getting Started

## What you need

- A Kubernetes cluster.
- Sealed Secrets (recommended) or another secret manager.
- An Anthropic API key.
- A Slack app with a bot token (`xoxb-`) and an app token (`xapp-`) for Socket Mode.
- A container registry to push images.

## Pick a mode

There are two ways to run Lucas:

1. **Interactive agent + dashboard**
This is a long-running Slack bot that also does scheduled scans. Use the manifests in `k8s/`.

2. **CronJob mode**
This runs on a schedule, writes results to SQLite, and can notify Slack via webhook. Use `k8s/cronjob.yaml`.

## Minimal steps (interactive agent)

1. Create the namespace, PVCs, and RBAC.
2. Create secrets for the Anthropic API key and Slack tokens.
3. Apply `k8s/agent-deployment.yaml` and `k8s/dashboard-deployment.yaml`.
4. Port-forward the dashboard service.
5. Invite the bot to a channel and `@lucas help`.

See **Deployment** for concrete commands and the exact manifest list.
