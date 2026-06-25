# Operations — Deployment and Updates

Recommended method: **Docker Compose** — single command, no system dependencies beyond Docker, identical environment on every machine.

The standard setup runs **two services on the same machine**:

| Service | Port | Image tag |
|---|---|---|
| Production | `5000` | `ksef-integration-api:stable` |
| Development | `5001` | `ksef-integration-api:latest` |

---

## First deployment (Docker)

### Option A — with repository access

```bash
git clone https://github.com/tech-dra-kbj/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API

# Build both image tags
./build-image.sh stable
./build-image.sh latest

# Start both services
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d
```

### Option B — without repository access (image as tar archive)

Deliver both tar files to the target machine, then:

```bash
docker load -i ksef-integration-api_stable.tar
docker load -i ksef-integration-api_latest.tar

docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d
```

---

## Verify after deployment

```bash
docker ps --filter name=ksef
```

Expected — both containers healthy:
```
ksef-encryptor      ksef-integration-api:stable   0.0.0.0:5000->5000/tcp
ksef-encryptor-dev  ksef-integration-api:latest   0.0.0.0:5001->5000/tcp
```

```bash
curl http://localhost:5000/health
curl http://localhost:5001/health
```

Expected response (both):
```json
{"status":"ok","service":"KSeF Integration API","version":"1.3.0"}
```

---

## Updating the service (Docker)

### With repository access

```bash
git pull

./build-image.sh stable
./build-image.sh latest

docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d --no-deps ksef-encryptor
```

`--no-deps` restarts only the application container without touching other services.

### Without repository access (tar delivery)

```bash
# On the build machine
./build-image.sh stable
./build-image.sh latest
# Transfer both tar files to the server

# On the server
docker load -i ksef-integration-api_stable.tar
docker load -i ksef-integration-api_latest.tar

docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d --no-deps ksef-encryptor
```

---

## Updating the service (systemd)

```bash
cd /home/ubuntu/KSeF-RSA-Encryptor-API
git pull

source .venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart ksef-encryptor.service
sudo systemctl status ksef-encryptor.service
```

---

## Checking logs

**Docker:**
```bash
docker logs ksef-encryptor     --tail 50 -f   # prod
docker logs ksef-encryptor-dev --tail 50 -f   # dev
```

**systemd:**
```bash
sudo journalctl -u ksef-encryptor.service -n 50 -f
# or from file:
tail -f /var/log/encrypt_service.log
```

---

## Rollback

**Docker:**
```bash
# Load previous images (if retained)
docker load -i ksef-integration-api_stable_prev.tar
docker load -i ksef-integration-api_latest_prev.tar

docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d --no-deps ksef-encryptor
```

**systemd:**
```bash
git checkout <previous-tag>
sudo systemctl restart ksef-encryptor.service
```
