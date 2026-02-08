#!/bin/bash
# Docker Hub Publishing Script
# Publikuje Docker image na Docker Hub s tagem latest
# Použití: ./scripts/docker_publish.sh <dockerhub_user> <image_name>

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <dockerhub_user> <image_name>"
    echo "Example: $0 myuser gql-evolution"
    exit 1
fi

DOCKERHUB_USER=$1
IMAGE_NAME=$2
FULL_IMAGE_NAME="${DOCKERHUB_USER}/${IMAGE_NAME}:latest"

echo "Building Docker image: ${FULL_IMAGE_NAME}"
docker build -t "${FULL_IMAGE_NAME}" .

echo "Logging in to Docker Hub..."
docker login

echo "Pushing image to Docker Hub: ${FULL_IMAGE_NAME}"
docker push "${FULL_IMAGE_NAME}"

echo "✅ Successfully published ${FULL_IMAGE_NAME} to Docker Hub"
echo "Verify with: docker pull ${FULL_IMAGE_NAME}"
