# Runbooks

Runbooks live in `src/agent/runbooks/` and are loaded by the agent. You can add your own runbooks (Markdown) to capture team-specific procedures and escalation rules, then rebuild the agent image.

## CrashLoopBackOff

- Check pod events and logs.
- Do not change app code.
- Escalate if the issue is not config or a simple health check.

## ImagePullBackOff

- Check pod events for auth, tag, or network errors.
- Do not change image tags or credentials.
- Escalate to the owning team.

## OOMKilled

- Verify memory limits and recent usage.
- Allowed fix: increase memory limit in small steps.
- Escalate if limits need to exceed 4Gi or if leaks are suspected.
