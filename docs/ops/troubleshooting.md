# Troubleshooting

## Slack bot does not respond

- Confirm `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are set.
- Confirm the app is in Socket Mode.
- Check `kubectl logs` for auth errors.

## Scheduled scans not running

- Check `SRE_ALERT_CHANNEL` is set.
- Check `SCAN_INTERVAL_SECONDS` is set to a positive value.
- Verify the agent pod is running.

## Dashboard shows no data

- Confirm the agent and dashboard use the same PVC (`lucas-data`).
- Check `SQLITE_PATH` in both deployments.
- Open `/health` on the dashboard service.

## Permission errors in /data or /home/claude/.claude

- Ensure the `fix-permissions` init container is running.
- Confirm the PVCs are bound and mounted.
