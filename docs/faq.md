# FAQ

---

## Table of Contents

1. [What is the recommended way to run the service in production?](#what-is-the-recommended-way-to-run-the-service-in-production)
2. [How do I check which version is running?](#how-do-i-check-which-version-is-running)
3. [Health response looks different from documentation](#health-response-looks-different-from-documentation)
4. [Network flow — how does SAP connect to the API?](#network-flow--how-does-sap-connect-to-the-api)
5. [Docker: starting the dev stack removes the prod container](#docker-starting-the-dev-stack-removes-the-prod-container)
6. [Port 5000 already in use](#port-5000-already-in-use)
7. [git pull says "divergent branches"](#git-pull-says-divergent-branches--what-do-i-do)
8. [SQLite database locked during startup](#sqlite-database-locked-during-startup)
9. [Node/PDF bridge not found](#nodepdf-bridge-not-found)
10. [The service starts but `/get_pub_cert` or `/consume` returns an error](#the-service-starts-but-get_pub_cert-or-consume-returns-an-error)
11. [`/generatePDF` returns "Unsupported invoice version: unknown"](#generatepdf-returns-unsupported-invoice-version-unknown)
12. [RHEL — Docker repository blocked by firewall](#rhel--docker-repository-blocked-by-firewall)
13. [Podman — `systemctl --user` fails with "No medium found"](#podman--systemctl---user-fails-with-no-medium-found)
14. [Good practices](#good-practices)

---

## What is the recommended way to run the service in production?

**Docker Compose is the recommended deployment method.** It guarantees an identical, reproducible environment on every machine regardless of the host OS configuration.

The only configuration that should differ between environments is **environment variables** — port number, number of workers, paths to Node.js binaries, etc. These are set in the compose override files (`docker-compose.prod.yml`, `docker-compose.dev.yml`) or passed with `-e` flags. No source files should ever be modified on the server.

```
What belongs on the server:
  ✓ docker-compose.yml          base config
  ✓ docker-compose.prod.yml     prod overrides (port, image tag)
  ✓ docker-compose.dev.yml      dev overrides (port, image tag)
  ✓ ksef-integration-api.tar    pre-built image (if no repo access)

What does NOT belong on the server:
  ✗ edits to encrypt_service.py, routes/, core/, swaggerapi.yaml, etc.
  ✗ local git commits
  ✗ manual pip installs
```

If a configuration change is needed (e.g. different port), edit the relevant environment variable in the compose override file and restart the container:

```bash
# Example: change prod port to 8080 in docker-compose.prod.yml, then:
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
```

Any change to application logic must go through the normal development cycle: code change → tests → build new image → deliver to server.

---

## How do I check which version is running?

```bash
curl http://localhost:5000/health
curl http://localhost:5001/health
```

Response includes the version field:
```json
{"status":"ok","service":"KSeF Integration API","version":"1.3.0"}
```

---

## Health response looks different from documentation

Older builds of the service returned a shorter response without a `version` field:

```json
{"status":"ok","service":"KSeF RSA Encryptor"}
```

Newer builds (v1.3.0+) return:

```json
{"status":"ok","service":"KSeF Integration API","version":"1.3.x"}
```

The service name was also changed from `KSeF RSA Encryptor` to `KSeF Integration API`. If you are integrating an automated health check, rely only on `status == "ok"` to remain compatible with both old and new builds.

---

## Network flow — how does SAP connect to the API?

**SAP systems initiate the HTTP connection.** The API does not call SAP back.

```
SAP system  -->  TCP/5000  -->  ksef-encryptor (PROD)
SAP system  -->  TCP/5001  -->  ksef-encryptor-dev (DEV)
```

The API listens on the host port, receives the request, processes it, and replies on the same TCP session. No separate outbound connection from the API host to SAP is required in the standard flow.

Firewall rules should allow inbound TCP on ports 5000 and 5001 from SAP hosts to the API host. No outbound SAP-specific rules are needed on the API host side.

---

## Docker: starting the dev stack removes the prod container

**Cause:** Running `docker compose` without `-p` uses the same default project name for both stacks, so one overwrites the other.

**Fix:** Always use `-p` to separate the two stacks:
```bash
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d
```

Both containers will run simultaneously:
```
ksef-encryptor      0.0.0.0:5000->5000/tcp   (prod)
ksef-encryptor-dev  0.0.0.0:5001->5000/tcp   (dev)
```

---

## Port 5000 already in use

**Symptom:** Container fails to start or `docker compose up` reports port already allocated.

**Check what owns the port:**
```bash
ss -lntp | grep -E ':5000|:5001'
```

**If the old systemd service owns the port:**
```bash
sudo systemctl stop encrypt_service.service
sudo systemctl disable encrypt_service.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

Verify the port is free, then start the Docker stack:
```bash
ss -lntp | grep ':5000' || echo "port free"
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

If the old unit file is still visible even after disabling:
```bash
sudo rm -f /etc/systemd/system/encrypt_service.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

Expected result:
```
Unit encrypt_service.service could not be found.
```

---

## git pull says "divergent branches" — what do I do?

**Symptom:**
```
hint: You have divergent branches and need to specify how to reconcile them.
fatal: Need to specify how to reconcile divergent branches.
```

**Cause:** The local `main` on the server has commits that differ from the remote. This usually happens when someone ran `git commit --amend`, `git rebase`, or a reset on the server, which rewrote commit history. Git now sees two separate lines of history even if commit messages look the same.

**The server should never have local commits** — it only pulls code, it does not introduce changes. The correct fix is a hard reset to remote, not a merge or rebase.

**Fix:**

First, check if any tracked files were modified locally on the server:
```bash
git status
git diff
```

If there are local modifications to tracked files (e.g. someone manually edited `encrypt_service.py`), back them up before proceeding:
```bash
cp encrypt_service.py encrypt_service.py.bak
```

Then reset to remote:
```bash
git fetch origin
git reset --hard origin/main
```

Restart the service:
```bash
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
```

Verify:
```bash
curl http://localhost:5000/health
```

> `git reset --hard` only affects files tracked by git. Runtime data such as the key database (`instance/keys.db`) and log files are not touched.

---

## SQLite database locked during startup

**Observed log:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Gunicorn starts multiple workers simultaneously. Each worker imports the application module and calls `init_db()`, which sets `PRAGMA journal_mode=WAL`. This requires an exclusive lock on the database file, and two workers racing for it causes the error.

**Fix (already applied in v1.3.0+):** Gunicorn is started with `--preload`, which loads the application once in the master process before forking workers. Workers inherit the already-initialized state and do not call `init_db()` again.

If you see this error on an older build, verify the Dockerfile contains `--preload`:
```
gunicorn --workers ${WORKERS} --threads ${THREADS} --preload --bind 0.0.0.0:${PORT} encrypt_service:app
```

If the error appears only once during the very first container start and the container subsequently becomes healthy, it was a one-time race during initialization. If it repeats on every start, check `KEY_DB_PATH`, file permissions, and whether `--preload` is present.

---

## Node/PDF bridge not found

**Symptom:** `/generatePDF` returns an error about Node.js or the bridge script not being found.

**Check paths inside the container:**
```bash
docker exec ksef-encryptor sh -c '
echo "PWD=$(pwd)"
echo "KSEF_NODE_BIN=$KSEF_NODE_BIN"
echo "KSEF_PDF_BRIDGE_PATH=$KSEF_PDF_BRIDGE_PATH"
echo "KSEF_PDF_MODULE_PATH=$KSEF_PDF_MODULE_PATH"
which node
node -v
ls -l "$KSEF_PDF_BRIDGE_PATH"
ls -l "$KSEF_PDF_MODULE_PATH"
'
```

**Correct values inside Docker:**
```
KSEF_NODE_BIN=node
KSEF_PDF_BRIDGE_PATH=./pdf_generator_bridge.mjs
KSEF_PDF_MODULE_PATH=./pdf-generator/dist/ksef-fe-invoice-converter.js
```

**Wrong values** (host paths that do not exist inside the container):
```
/home/ksef/.nvm/versions/node/v20.x.x/bin/node
/opt/ksef/prod/KSeF-RSA-Encryptor-API/pdf_generator_bridge.mjs
```

If the compose override file sets `KSEF_NODE_BIN` to an absolute host path, remove that override and let the container default take effect.

---

## The service starts but `/get_pub_cert` or `/consume` returns an error

Check the Python version inside the container:
```bash
docker exec ksef-encryptor python --version
```

Python 3.10 is required. If the version is lower, rebuild the Docker image from the provided `Dockerfile` which uses `python:3.10-slim`.

---

## `/generatePDF` returns "Unsupported invoice version: unknown"

This is expected behaviour when sending XML that does not conform to a supported KSeF invoice schema (FA(1), FA(2), FA(3), FA_RR). The Node.js bridge is working correctly — the error comes from the PDF generator, not the API.

Check that:
- The XML is a valid KSeF invoice document.
- `pdf-generator/dist/ksef-fe-invoice-converter.js` exists in the expected path.
- Node.js 20+ is available (`node --version`).

---

## RHEL — Docker repository blocked by firewall

**Symptom:** `curl` or `dnf` to `download.docker.com` times out during Docker CE installation.

**Cause:** The server's firewall blocks outbound HTTPS to Docker's repository.

**Solution:** Use **rootless Podman**, which is available in the standard RHEL repositories and does not require internet access to Docker's CDN.

```bash
dnf install -y podman podman-docker container-tools
loginctl enable-linger ksef
```

`podman-docker` provides a `docker` CLI shim so existing `docker compose` commands work without changes.

> Rootless Podman does not require adding the user to a `docker` group — it runs entirely in user space.

---

## Podman — `systemctl --user` fails with "No medium found"

**Symptom:**
```
Failed to connect to bus: No medium found
```

**Cause:** The `ksef` user session was not fully initialized — D-Bus user session bus is not available when running via `sudo su - ksef` in some environments.

**Workaround:** Set the runtime directory explicitly:
```bash
UID_KSEF=$(id -u ksef)

XDG_RUNTIME_DIR=/run/user/$UID_KSEF \
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$UID_KSEF/bus \
runuser -u ksef -- systemctl --user daemon-reload
```

Alternatively, log in directly as `ksef` via SSH or use `machinectl shell ksef@` if available.

---

## Good practices

**Run the service as a dedicated system user.**
Create a dedicated `ksef` user with no login shell and add it to the `docker` group. Never run containers as `root` or as a personal developer account. This limits the blast radius of any misconfiguration and keeps file ownership consistent across directories.

```bash
sudo useradd -m -s /bin/bash ksef
sudo usermod -aG docker ksef
sudo mkdir -p /opt/ksef/{dev,prod,archive}
sudo chown -R ksef:ksef /opt/ksef
```

**Archive old systemd deployments before switching to Docker.**
Before removing an existing `encrypt_service.service`, save both the unit file and the application directory:

```bash
BACKUP_TS=$(date +%F_%H%M%S)

sudo tar -czf "/opt/ksef/archive/old-app-${BACKUP_TS}.tar.gz" \
  -C /home/ubuntu KSeF-RSA-Encryptor-API

sudo cp -a /etc/systemd/system/encrypt_service.service \
  "/opt/ksef/archive/encrypt_service.service-${BACKUP_TS}"

sudo systemctl cat encrypt_service.service \
  | sudo tee "/opt/ksef/archive/encrypt_service.service.cat-${BACKUP_TS}.txt" >/dev/null
```

Only remove the unit file after the Docker stack is verified healthy.

**Never modify application files directly on the server.**
All changes go through git → build → image delivery. The server is a runtime environment, not a development machine.

**Use the `-p` flag every time with `docker compose`.**
Running without `-p ksef-prod` or `-p ksef-dev` on a shared host will silently overwrite the other stack. Make it a habit even when running a single stack.

**Keep PROD and DEV in separate directories.**
```
/opt/ksef/prod/KSeF-RSA-Encryptor-API  →  branch main
/opt/ksef/dev/KSeF-RSA-Encryptor-API   →  feature branch
```
This prevents accidental cross-contamination of compose files and git state.

**Archive before any major change.**
Before migrating, updating, or stopping a running service, save a snapshot:
```bash
BACKUP_TS=$(date +%F_%H%M%S)
sudo tar -czf "/opt/ksef/archive/backup-${BACKUP_TS}.tar.gz" \
  -C /opt/ksef/prod KSeF-RSA-Encryptor-API
```

**Always verify after deployment.**
```bash
curl -s http://localhost:5000/health; echo
curl -s http://localhost:5001/health; echo
docker ps --filter name=ksef
```

**Use pre-built image tars on firewall-restricted servers.**
Build the image on a machine with internet access, export it, and transfer via SCP:
```bash
# build machine
./build-image.sh stable
scp ksef-integration-api_stable.tar ksef@server:/opt/ksef/archive/

# server
docker load -i /opt/ksef/archive/ksef-integration-api_stable.tar
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Do not use host-absolute paths for Node.js inside Docker.**
Set `KSEF_NODE_BIN=node` and use relative paths for bridge and module — the container has its own `PATH` and its own filesystem.
