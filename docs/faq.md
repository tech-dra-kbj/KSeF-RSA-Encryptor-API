# FAQ

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
# Docker
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d --no-deps ksef-encryptor

# systemd
sudo systemctl restart ksef-encryptor.service
```

Verify:
```bash
curl http://localhost:5000/health
```

> `git reset --hard` only affects files tracked by git. Runtime data such as the key database (`instance/keys.db`) and log files are not touched.

---

## The service starts but `/get_pub_cert` or `/consume` returns an error

Check the Python version inside the container or virtualenv:
```bash
# Docker
docker exec ksef-encryptor python --version

# systemd
python --version
```

Python 3.10 is required. If the version is lower, update Python or rebuild the Docker image from the provided `Dockerfile` which uses `python:3.10-slim`.

---

## `/generatePDF` returns "Unsupported invoice version: unknown"

This is expected behaviour when sending XML that does not conform to a supported KSeF invoice schema (FA(1), FA(2), FA(3), FA_RR). The Node.js bridge is working correctly — the error comes from the PDF generator, not the API.

Check that:
- The XML is a valid KSeF invoice document.
- `pdf-generator/dist/ksef-fe-invoice-converter.js` exists in the expected path.
- Node.js 20+ is available (`node --version`).

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

## How do I check which version is running?

```bash
curl http://localhost:5000/health
curl http://localhost:5001/health
```

Response includes the version field:
```json
{"status":"ok","service":"KSeF Integration API","version":"1.3.0"}
```
