#!/usr/bin/env bash
set -euo pipefail

# Run from anywhere: resolve the repository root from this script's location.
DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${DOCKER_DIR}")"

TAG="${1:-latest}"

APP_IMAGE="ksef-integration-api"
PROXY_IMAGE="ksef-ssl-proxy"

APP_FILE="${REPO_ROOT}/${APP_IMAGE}_${TAG}.tar"
PROXY_FILE="${REPO_ROOT}/${PROXY_IMAGE}_${TAG}.tar"

# --pull on both: the proxy's whole point is picking up a current nginx-alpine base,
# and a cached one silently reinstates the outdated packages we just moved off.

echo "Building ${APP_IMAGE}:${TAG}"
docker build --pull -t "${APP_IMAGE}:${TAG}" -f "${DOCKER_DIR}/Dockerfile" "${REPO_ROOT}"

echo "Exporting ${APP_IMAGE}:${TAG} to ${APP_FILE}"
docker save -o "${APP_FILE}" "${APP_IMAGE}:${TAG}"

# The TLS proxy builds from docker/proxy, not the repository root: its Dockerfile
# copies nginx.conf.template and entrypoint.sh by paths relative to that directory.
echo "Building ${PROXY_IMAGE}:${TAG}"
docker build --pull -t "${PROXY_IMAGE}:${TAG}" "${DOCKER_DIR}/proxy"

echo "Exporting ${PROXY_IMAGE}:${TAG} to ${PROXY_FILE}"
docker save -o "${PROXY_FILE}" "${PROXY_IMAGE}:${TAG}"

APP_SIZE=$(du -sh "${APP_FILE}" | cut -f1)
PROXY_SIZE=$(du -sh "${PROXY_FILE}" | cut -f1)

echo ""
echo "Done."
echo "  ${APP_FILE} (${APP_SIZE})"
echo "  ${PROXY_FILE} (${PROXY_SIZE})"
echo ""
echo "Transfer the files to the target machine, then load them with:"
echo "  docker load -i $(basename "${APP_FILE}")"
echo "  docker load -i $(basename "${PROXY_FILE}")"

if [ "${TAG}" != "stable" ]; then
  echo ""
  echo "Note: docker/docker-compose.ssl.yml consumes ${PROXY_IMAGE}:stable."
  echo "      Build with 'stable' as well, or the TLS overlay keeps the previous proxy."
fi
