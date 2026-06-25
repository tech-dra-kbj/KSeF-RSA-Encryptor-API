#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="ksef-integration-api"
TAG="${1:-latest}"
OUTPUT_FILE="${IMAGE_NAME}_${TAG}.tar"

echo "Building Docker image: ${IMAGE_NAME}:${TAG}"
docker build -t "${IMAGE_NAME}:${TAG}" .

echo "Exporting image to: ${OUTPUT_FILE}"
docker save -o "${OUTPUT_FILE}" "${IMAGE_NAME}:${TAG}"

SIZE=$(du -sh "${OUTPUT_FILE}" | cut -f1)
echo "Done. File: ${OUTPUT_FILE} (${SIZE})"
echo ""
echo "Transfer the file to the target machine, then load it with:"
echo "  docker load -i ${OUTPUT_FILE}"
