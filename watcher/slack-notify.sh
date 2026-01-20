#!/bin/bash
# Slack notification helper for Clopus Watcher
# Usage: slack-notify.sh <status> <namespace> <run_id> <pod_count> <error_count> <fix_count> <summary>

set -e

# Check if Slack is configured
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "Slack notifications disabled (SLACK_WEBHOOK_URL not set)"
    exit 0
fi

STATUS="$1"
NAMESPACE="$2"
RUN_ID="$3"
POD_COUNT="$4"
ERROR_COUNT="$5"
FIX_COUNT="$6"
SUMMARY="$7"
MODE="${WATCHER_MODE:-autonomous}"

# Determine emoji and color based on status
case "$STATUS" in
    ok)
        EMOJI=":white_check_mark:"
        COLOR="#36a64f"
        TITLE="All Clear"
        ;;
    fixed)
        EMOJI=":wrench:"
        COLOR="#f2c744"
        TITLE="Issues Fixed"
        ;;
    failed)
        EMOJI=":x:"
        COLOR="#dc3545"
        TITLE="Issues Found"
        ;;
    issues_found)
        EMOJI=":warning:"
        COLOR="#ff9800"
        TITLE="Issues Detected"
        ;;
    *)
        EMOJI=":information_source:"
        COLOR="#6c757d"
        TITLE="Watcher Report"
        ;;
esac

# Build human-readable message
if [ "$STATUS" = "ok" ]; then
    MESSAGE="Hey! Just finished checking *${NAMESPACE}* namespace. Everything looks good! :tada:\n\nChecked *${POD_COUNT}* pods, no issues found."
elif [ "$STATUS" = "fixed" ]; then
    MESSAGE="Heads up! Found some issues in *${NAMESPACE}* and fixed them.\n\n:mag: Checked *${POD_COUNT}* pods\n:warning: Found *${ERROR_COUNT}* issues\n:white_check_mark: Fixed *${FIX_COUNT}* of them\n\n${SUMMARY}"
elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "issues_found" ]; then
    if [ "$MODE" = "report" ]; then
        MESSAGE=":eyes: Report from *${NAMESPACE}* namespace:\n\n:mag: Checked *${POD_COUNT}* pods\n:warning: Found *${ERROR_COUNT}* issues that need attention\n\n${SUMMARY}\n\n_Running in report-only mode - no fixes attempted._"
    else
        MESSAGE=":rotating_light: Alert from *${NAMESPACE}* namespace!\n\n:mag: Checked *${POD_COUNT}* pods\n:warning: Found *${ERROR_COUNT}* issues\n:x: Could not auto-fix\n\n${SUMMARY}\n\n_Manual intervention may be required._"
    fi
else
    MESSAGE="Watcher run #${RUN_ID} completed for *${NAMESPACE}*.\n\nPods: ${POD_COUNT} | Errors: ${ERROR_COUNT} | Fixes: ${FIX_COUNT}"
fi

# Build Slack payload
PAYLOAD=$(cat <<EOF
{
    "attachments": [
        {
            "color": "${COLOR}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "${EMOJI} Clopus Watcher: ${TITLE}",
                        "emoji": true
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "${MESSAGE}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Run #${RUN_ID} | Mode: ${MODE} | $(date '+%Y-%m-%d %H:%M:%S UTC')"
                        }
                    ]
                }
            ]
        }
    ]
}
EOF
)

# Send to Slack
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$SLACK_WEBHOOK_URL")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "Slack notification sent successfully"
else
    echo "Failed to send Slack notification (HTTP $HTTP_STATUS)"
fi
