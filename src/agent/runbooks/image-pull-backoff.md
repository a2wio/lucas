# ImagePullBackOff

## Symptoms
- Pod status shows `ImagePullBackOff` or `ErrImagePull`
- Pod stuck in pending/waiting state
- Events show "Failed to pull image"

## Diagnosis
1. Check pod events: `kubectl describe pod <name> -n <namespace>`
2. Look for the specific error message:
   - "unauthorized" = auth issue
   - "not found" = wrong image name/tag
   - "timeout" = network issue

## Approved Fixes

### Image tag doesn't exist
If the image tag is wrong or doesn't exist:
1. Report the issue with the exact image:tag
2. Do NOT change the image - escalate to team

### Registry authentication
If "unauthorized" error:
1. Check if imagePullSecrets is configured: `kubectl get pod <name> -n <namespace> -o yaml | grep -A5 imagePullSecrets`
2. Report missing or incorrect credentials
3. Do NOT create secrets - escalate

### Network/timeout issues
If timeout or network error:
1. Check if other pods can pull images
2. Report as potential cluster network issue
3. Escalate to infrastructure team

## Escalate When
- Always escalate - ImagePullBackOff requires human intervention
- Never modify image references without explicit approval
