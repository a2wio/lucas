# Dashboard

The dashboard is a simple Go app that reads from SQLite.

## Login

Set credentials with:

- `AUTH_USER`
- `AUTH_PASS`

Defaults are `a2wmin` / `a2wssword`.

## Pages

- **Overview**: recent runs, latest run details, and log tail.
- **Sessions**: Slack sessions stored in SQLite.
- **Costs**: token usage and cost totals.
- **Runbooks**: static runbook summaries.

## Logs

The dashboard reads the last ~200 lines from `LOG_PATH` and shows them on the Overview page.
