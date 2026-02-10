---
layout: home
hero:
  name: "A2W: Lucas"
  text: "Autonomous Kubernetes operations & reliability agent"
  tagline: "Investigate, remediate, and drive lasting fixes."
  image:
    src: /logo-dark.png
    alt: A2W logo
  actions:
    - theme: brand
      text: Getting Started
      link: /guide/getting-started
    - theme: alt
      text: Deployment
      link: /ops/deployment
features:
  - title: Interactive Slack agent
    details: Ask Lucas to investigate pods, read logs, and report findings.
  - title: Scheduled scans
    details: Periodic checks for CrashLoopBackOff, ImagePullBackOff, and errors.
  - title: Dashboard
    details: Web UI for runs, sessions, and token/cost tracking.
---

## Quick Start

1. Create sealed secrets for the Anthropic API key and Slack tokens.
2. Deploy with ArgoCD or apply the manifests directly.
3. Open the dashboard and invite the bot to a Slack channel.

## Introduction

Lucas is a Kubernetes operations and reliability agent. It runs in your cluster, inspects pods and logs, and can report or remediate based on the mode you choose.

## Functionality

- Slack-first investigations with thread context and follow-ups.
- Scheduled scans across namespaces.
- Runbooks for approved fixes and escalation rules.
- Dashboard for runs, sessions, and token usage.

## Deployment

Pick one of these paths:

- ArgoCD: use the manifests as a source repo and let ArgoCD sync.
- Plain YAML: apply the files in `k8s/` with `kubectl`.

## What's in this repo

- `src/agent/`: Slack agent, scheduler, and runbooks.
- `src/dashboard/`: Go dashboard and templates.
- `k8s/`: Kubernetes manifests for agent, dashboard, and storage.
- `scripts/`: install script that generates manifests and sealed secrets.
