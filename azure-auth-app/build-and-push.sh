#!/bin/bash
# Build and push Docker image to GitHub Container Registry

set -e

# Configuration
REGISTRY="ghcr.io"
NAMESPACE=${GITHUB_REPOSITORY_OWNER:-"your-github-username"}
IMAGE_NAME="cids-auth"
TAG=${1:-"latest"}

# Full image name
FULL_IMAGE_NAME="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${TAG}"

echo "Building and pushing: ${FULL_IMAGE_NAME}"

# Check if logged in to GitHub Container Registry
if ! docker info 2>/dev/null | grep -q "${REGISTRY}"; then
    echo "Not logged in to ${REGISTRY}. Please run:"
    echo "echo \$GITHUB_TOKEN | docker login ${REGISTRY} -u \$GITHUB_USERNAME --password-stdin"
    exit 1
fi

# Build the image
echo "Building Docker image..."
docker build -t "${FULL_IMAGE_NAME}" .

# Tag as latest if building a version tag
if [[ $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    LATEST_TAG="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest"
    docker tag "${FULL_IMAGE_NAME}" "${LATEST_TAG}"
    echo "Also tagged as: ${LATEST_TAG}"
fi

# Push the image(s)
echo "Pushing Docker image..."
docker push "${FULL_IMAGE_NAME}"

if [[ ! -z $LATEST_TAG ]]; then
    docker push "${LATEST_TAG}"
fi

echo "Successfully pushed: ${FULL_IMAGE_NAME}"

# Optional: Generate and display image digest
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${FULL_IMAGE_NAME}" | cut -d'@' -f2)
echo "Image digest: ${DIGEST}"