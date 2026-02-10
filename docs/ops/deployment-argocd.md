# ArgoCD

Use ArgoCD to sync the `k8s/` directory from this repo.

## Basic flow

1. Create an ArgoCD Application that targets the repo and path `k8s/`.
2. Set the destination namespace to `a2w-lucas`.
3. Add secrets for `claude-auth` and `slack-bot`.
4. Sync the application.

## Notes

- Keep secrets out of Git; use Sealed Secrets or External Secrets.
- Update image tags in `k8s/` when you push new images.
- If you already manage RBAC or PVCs separately, remove those manifests from the app.

## ArgoCD patterns

You can manage this repo with either App of Apps or an ApplicationSet. Pick one.

**App of Apps**

Use a single root Application that points to a folder of child Applications. This is good when you want explicit, hand-written app definitions per component or environment.

Example layout:

- `argocd/apps/agent.yaml`
- `argocd/apps/dashboard.yaml`
- `argocd/apps/storage.yaml`
- `argocd/apps/root.yaml` (points to `argocd/apps/`)

**ApplicationSet**

Use an ApplicationSet to generate Applications from a list or directory. This is good when you have multiple environments or clusters.

Example (list generator):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: lucas
spec:
  generators:
    - list:
        elements:
          - name: dev
            namespace: a2w-lucas
          - name: prod
            namespace: a2w-lucas
  template:
    metadata:
      name: lucas-{{name}}
    spec:
      project: default
      source:
        repoURL: https://example.com/your/repo.git
        targetRevision: main
        path: k8s
      destination:
        server: https://kubernetes.default.svc
        namespace: {{namespace}}
      syncPolicy:
        automated: {}
```
