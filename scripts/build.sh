#!/bin/bash
set -e

REGISTRY="${REGISTRY:-ghcr.io/kubeden}"
TAG="${TAG:-latest}"

echo "Building Clopus Watcher images..."
echo "Registry: $REGISTRY"
echo "Tag: $TAG"

# Build watcher image
echo ""
echo "=== Building watcher image ==="
docker build -t "$REGISTRY/clopus-watcher:$TAG" -f Dockerfile.watcher .

# Build dashboard image
echo ""
echo "=== Building dashboard image ==="
docker build -t "$REGISTRY/clopus-watcher-dashboard:$TAG" -f Dockerfile.dashboard .

echo ""
echo "=== Build complete ==="
echo ""
echo "To push images:"
echo "  docker push $REGISTRY/clopus-watcher:$TAG"
echo "  docker push $REGISTRY/clopus-watcher-dashboard:$TAG"
