# Build Images

This repo ships three images.

## Agent (Slack)

```bash
podman build --platform=linux/amd64 -f Dockerfile.agent -t your-registry/lucas-agent:tag .
podman push your-registry/lucas-agent:tag
```

## Dashboard

```bash
podman build --platform=linux/amd64 -f Dockerfile.dashboard -t your-registry/lucas-dashboard:tag .
podman push your-registry/lucas-dashboard:tag
```

## Agent (CronJob)

```bash
podman build --platform=linux/amd64 -f Dockerfile.lucas -t your-registry/lucas:tag .
podman push your-registry/lucas:tag
```

Update the image tags in `k8s/` after pushing.
