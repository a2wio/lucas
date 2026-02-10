# Configuration

## Agent (interactive Slack)

Required:

- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`

Common:

- `SRE_MODE`: `autonomous` or `watcher`.
- `CLAUDE_MODEL`: `sonnet` or `opus`.
- `TARGET_NAMESPACE`: default namespace for interactive requests.
- `TARGET_NAMESPACES`: comma-separated list for scheduled scans.
- `SRE_ALERT_CHANNEL`: channel ID for scheduled scan alerts.
- `SCAN_INTERVAL_SECONDS`: seconds between scheduled scans.
- `SQLITE_PATH`: defaults to `/data/lucas.db`.
- `PROMPT_FILE`: defaults to `/app/master-prompt-interactive.md`.

Notes:

- If `SRE_ALERT_CHANNEL` is empty, scheduled scans are disabled.
- `SRE_MODE=watcher` uses the report-only prompt.

## Agent (CronJob mode)

Required:

- `TARGET_NAMESPACE`
- `SRE_MODE`: `autonomous` or `report`.
- `AUTH_MODE`: `api-key` or `credentials`.

If `AUTH_MODE=api-key`:

- `ANTHROPIC_API_KEY`

If `AUTH_MODE=credentials`:

- Mount `credentials.json` at `/secrets/credentials.json` or `$HOME/.claude/.credentials.json`.

Optional:

- `SLACK_WEBHOOK_URL`: enables Slack notifications.
- `SQLITE_PATH`: defaults to `/data/lucas.db`.

## Dashboard

- `SQLITE_PATH`: defaults to `/data/lucas.db`.
- `PORT`: defaults to `8080`.
- `LOG_PATH`: defaults to `/data/lucas.log`.
- `AUTH_USER`: defaults to `a2wmin`.
- `AUTH_PASS`: defaults to `a2wssword`.
