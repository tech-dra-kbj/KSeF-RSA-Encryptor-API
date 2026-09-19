# Operations — Deployment and Updates

Recommended method: **Docker Compose** — single command, no system dependencies beyond Docker, identical environment on every machine.

The standard setup runs **two services on the same machine**:

| Service | Port | Image tag |
|---|---|---|
| Production | `5000` | `ksef-integration-api:stable` |
| Development | `5001` | `ksef-integration-api:latest` |
| TLS proxy (optional) | `443`, `80` | `ksef-ssl-proxy:stable` |

The TLS proxy is an additive overlay: it changes nothing in the other files and the
application keeps publishing its own port. Add `-f docker/docker-compose.ssl.yml` to
every command below to include it. See [Deployment — TLS](deployment.md#tls-production)
for certificates and cipher configuration.

> **Keep the project name consistent.** `docker/docker-compose.yml` sets
> `name: ksef-integration-api`, which applies when `-p` is omitted. The commands below
> pass `-p ksef-prod` and `-p ksef-dev` to keep the two stacks apart. Mixing the two
> styles on one machine gives you duplicate stacks fighting over the same ports.

---

## First deployment (Docker)

### Option A — with repository access

```bash
git clone https://github.com/tech-dra-kbj/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API

# Builds both images and writes a tar for each. Pass the tag to build.
./docker/build-image.sh stable
./docker/build-image.sh latest

# Equivalent, without the tar archives:
# docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
#                -f docker/docker-compose.ssl.yml build --pull

# Start both services
docker compose -p ksef-prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
docker compose -p ksef-dev  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

### Option B — without repository access (image as tar archive)

Deliver both tar files to the target machine, then:

```bash
docker load -i ksef-integration-api_stable.tar
docker load -i ksef-integration-api_latest.tar
docker load -i ksef-ssl-proxy_stable.tar      # only if terminating TLS here

docker compose -p ksef-prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
docker compose -p ksef-dev  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
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
{"status":"ok","service":"KSeF Integration API","version":"1.4.0"}
```

With the TLS overlay running, the same check through the proxy:

```bash
curl -sk --resolve "$KSEF_SSL_DOMAIN:443:127.0.0.1" "https://$KSEF_SSL_DOMAIN/health"

# certificate chain and negotiated cipher
echo | openssl s_client -connect localhost:443 -tls1_2 \
  -CAfile docker/certs/ca.crt 2>/dev/null | grep -E "Protocol|Cipher|Verify return code"
```

`Verify return code: 0 (ok)` confirms clients will trust the chain once they have
`docker/certs/ca.crt`.

---

## Updating the service (Docker)

### With repository access

```bash
git fetch --tags origin
git checkout v1.4.0          # a tag, so the deployed state is reproducible

# --pull matters: proxy fixes come from a fresh base image, not from our layers
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
               -f docker/docker-compose.ssl.yml build --pull
docker tag ksef-integration-api:stable ksef-integration-api:latest

docker compose -p ksef-prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
               -f docker/docker-compose.ssl.yml up -d
docker compose -p ksef-dev  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --no-deps ksef-encryptor
```

`--no-deps` restarts only the application container without touching other services.
Drop it when the proxy image changed too, otherwise the old proxy keeps running.

### Without repository access (tar delivery)

```bash
# On the build machine — writes both tars next to the repository
./docker/build-image.sh stable
# Transfer the tar files to the server

# On the server
docker load -i ksef-integration-api_stable.tar
docker load -i ksef-ssl-proxy_stable.tar

docker compose -p ksef-prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --no-deps ksef-encryptor
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
docker logs ksef-ssl-proxy     --tail 50 -f   # TLS proxy, HTTP access log
```

The application log carries what the service itself reports, including rejected
requests with their error code — gunicorn runs without an access log, so the HTTP
request lines live in the proxy log instead:

```bash
# what we rejected and why
docker logs ksef-encryptor 2>&1 | grep -oE "code [0-9]{3,4}" | sort | uniq -c | sort -rn

# service faults only, skipping client errors
docker logs -f ksef-encryptor 2>&1 | grep -E "code 23[0-9]{2}|Traceback"

# real traffic, without the health probe every 30 s
docker logs -f ksef-ssl-proxy | grep -v '"GET /health'
```

> Both containers use the `json-file` log driver with no size limit, so logs grow until
> the disk fills. On a long-running deployment, cap them per service in the compose
> file:
>
> ```yaml
>     logging:
>       driver: json-file
>       options:
>         max-size: "10m"
>         max-file: "5"
> ```

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
docker load -i ksef-ssl-proxy_stable_prev.tar     # only if terminating TLS here

docker compose -p ksef-prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --no-deps ksef-encryptor
docker compose -p ksef-dev  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --no-deps ksef-encryptor
```

**systemd:**
```bash
git checkout <previous-tag>
sudo systemctl restart ksef-encryptor.service
```
