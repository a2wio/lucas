# CrashLoopBackOff

## Symptoms
- Pod status shows `CrashLoopBackOff`
- Pod keeps restarting with increasing backoff
- `kubectl get pods` shows high restart count

## Diagnosis
1. Check pod events: `kubectl describe pod <name> -n <namespace>`
2. Check logs: `kubectl logs <name> -n <namespace> --previous`
3. Look for exit codes and error messages

## Approved Fixes

### Application error in logs
If logs show clear application error:
1. Report the error to the team
2. Do NOT attempt code fixes
3. Escalate immediately

### Missing config/secret
If logs show missing environment variable or config:
1. Check if ConfigMap/Secret exists: `kubectl get configmap,secret -n <namespace>`
2. Report missing configuration
3. Escalate - do not create configs without approval

### Health check failing
If the container starts but health check fails:
1. Check if the health endpoint is correct
2. Check if the service needs more startup time
3. Report findings and recommend increasing `initialDelaySeconds`

### OOMKilled causing crash loop
If previous termination reason is OOMKilled:
- Follow the oom-killed.md runbook

## Escalate When
- Always escalate CrashLoopBackOff - it indicates application issues
- Only apply fixes explicitly documented above
