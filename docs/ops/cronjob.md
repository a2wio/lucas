# CronJob Mode

CronJob mode runs a batch scan and writes a report to SQLite. It can also notify Slack via webhook.

## Manifest

Use `k8s/cronjob.yaml` and adjust:

- `schedule`
- `image`
- `TARGET_NAMESPACE`
- `SRE_MODE` (`autonomous` or `report`)
- `AUTH_MODE` (`api-key` or `credentials`)
- `SLACK_WEBHOOK_URL` (optional)

## Auth options

API key:

- Set `AUTH_MODE=api-key`.
- Provide `ANTHROPIC_API_KEY` in a secret.

Credentials file:

- Set `AUTH_MODE=credentials`.
- Mount `credentials.json` at `/secrets/credentials.json`.

## Storage

The CronJob writes to the same PVC (`lucas-data`). This lets the dashboard read its results.
