# OOMKilled - Out of Memory

## Symptoms
- Pod status shows `OOMKilled`
- Container terminated with exit code 137
- `kubectl describe pod` shows "OOMKilled" in last state

## Diagnosis
1. Check current memory limits: `kubectl describe pod <name> -n <namespace>`
2. Check actual memory usage before crash (if metrics available)
3. Check logs for memory-related errors

## Approved Fixes

### Increase memory limit (standard fix)
If the pod is consistently hitting memory limits:
```bash
kubectl set resources deployment/<deployment-name> -n <namespace> --limits=memory=<new-limit>
```

Recommended increments:
- 256Mi -> 512Mi
- 512Mi -> 1Gi
- 1Gi -> 2Gi

### Restart pod (temporary)
If immediate relief needed while investigating:
```bash
kubectl delete pod <pod-name> -n <namespace>
```

## Escalate When
- Memory usage keeps growing (possible memory leak)
- Increasing limits doesn't help
- Pod needs more than 4Gi memory
