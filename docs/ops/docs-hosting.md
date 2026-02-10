# Docs Hosting

The docs site is built with VitePress and can be hosted as a static site. This repo includes a Dockerfile and Kubernetes manifests to run it in the same cluster as Lucas.

## Build the docs image

```bash
podman build --platform=linux/amd64 -f Dockerfile.docs -t your-registry/lucas-docs:tag .
podman push your-registry/lucas-docs:tag
```

Update the image tag in `k8s/docs-deployment.yaml`.

## Kubernetes manifests

- `k8s/docs-deployment.yaml`
- `k8s/docs-service.yaml`
- `k8s/docs-ingress.yaml`

Apply them:

```bash
kubectl apply -f k8s/docs-deployment.yaml
kubectl apply -f k8s/docs-service.yaml
kubectl apply -f k8s/docs-ingress.yaml
```

Update the host in `k8s/docs-ingress.yaml` to your domain.

## Local preview

```bash
cd docs
npm install
npm run dev
```

## Build output

The static site is generated at `docs/.vitepress/dist`.

## llms.txt

The docs include `docs/public/llms.txt` for LLM-friendly indexing. It is served at `/llms.txt`.
