---
name: lucas-runbook
description: Lucas runbook-driven troubleshooting for Kubernetes issues. Use when investigating pod errors, crashes, restarts, or any Kubernetes problem. Automatically search runbooks before taking action.
allowed-tools: Read, Glob, Grep, WebFetch
---

# Lucas Runbook-Driven Troubleshooting

You are operating in **runbook-driven mode**. Before taking any remediation action, you MUST search for and follow approved runbooks.

## Runbook Sources

Search these locations for runbooks:

### Local Runbooks
- Path: `/runbooks`
- Search using: `Glob pattern="**/*.md" path="/runbooks"`
- Read matching files to find relevant procedures

### External Documentation (if configured)
- Check environment or config for external URLs
- Use WebFetch to retrieve external runbook content

## Procedure

When you identify a Kubernetes issue:

1. **Identify the error type** (OOMKilled, CrashLoopBackOff, ImagePullBackOff, etc.)

2. **Search for matching runbook**:
   ```
   Glob pattern="**/*oom*.md" path="/runbooks"
   Glob pattern="**/*crash*.md" path="/runbooks"
   Glob pattern="**/*image*.md" path="/runbooks"
   ```

3. **Read the runbook** if found

4. **Follow the runbook EXACTLY**:
   - Use only the approved diagnostic commands
   - Apply only the approved fixes
   - Escalate when the runbook says to escalate

5. **If NO runbook found**:
   - Do NOT attempt fixes
   - Report what you observed
   - Ask: "No runbook found for this issue. How should I proceed?"

## Important Rules

- ALWAYS cite which runbook you're following
- NEVER improvise fixes outside of runbooks
- If a runbook says "escalate", do NOT attempt the fix yourself
- Document what you did and the outcome

## Example

When you see OOMKilled:
1. Search: `Glob pattern="**/*oom*.md" path="/runbooks"`
2. Find: `oom-killed.md`
3. Read: The runbook says to increase memory limits
4. Say: "Following runbook `oom-killed.md`: Increasing memory limit from 256Mi to 512Mi"
5. Execute the approved fix
6. Verify and report outcome
