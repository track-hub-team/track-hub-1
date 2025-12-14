
---


# Self-Hosted Deployment Guide (Proxmox)


## Server Specifications

The runtime environment uses the following hardware:

- **CPU:** AMD Ryzen 5 5650G
- **RAM:** 32 GB
- **Storage:**
  - 250 GB SSD mirror (RAID 1) for system and critical data
  - 300 GB NVMe dedicated for the application and its volumes

This ensures high performance, redundancy, and enough space for TrackHub services and workloads.



## Summary

This document describes how to deploy TrackHub on a self-managed Proxmox server with MariaDB (TLS), two environments (PRE/PROD), Docker containers, Cloudflare Tunnel, and automated deployment via GitHub Actions.

- Automatic deployments are triggered on pushes to the `trunk` (PRE) and `main` (PROD) branches.
- The self-hosted runner executes the jobs defined in `.github/workflows/CD_selfhosted.yml`.
- The pipeline performs:
  1. Code checkout
  2. Docker image build
  3. Container (or Docker Compose stack) deployment
  4. (Optional) Test/lint execution before deployment
- The pipeline status can be monitored from the Actions tab in the GitHub repository.

---



## 1. TLS Configuration in MariaDB

**On the host running MariaDB (not in the container):**

1. Create the SSL directory and the CA.
2. Generate the server key and CSR for `host.docker.internal`.
3. Sign the server certificate with your CA.
4. Configure MariaDB (`/etc/mysql/mariadb.conf.d/50-server.cnf`):

  ```
  [mysqld]
  ssl-ca=/etc/mysql/ssl/ca.pem
  ssl-cert=/etc/mysql/ssl/server-cert.pem
  ssl-key=/etc/mysql/ssl/server-key.pem
  # require_secure_transport=ON (opcional)
  ```


5. Restart MariaDB and verify with:

  ```
  sudo mariadb -e "SHOW VARIABLES LIKE 'have_ssl';"
  ```

---




## 2. Docker Image for Self-Hosted

- Dockerfile: `docker/images/Dockerfile.selfhosted`
- Entrypoint: `docker/entrypoints/selfhosted_entrypoint.sh`
- Main features:
  - Waits for MariaDB to be available (with TLS if `MARIADB_SSL_CA` is set)
  - Runs Alembic migrations
  - **Automatically runs seeders if preproduction environment is detected**
  - Starts Gunicorn

**Note on seeders:**
If the environment variable `FLASK_ENV` is `preproduction` or `ENV` is `pre`, the entrypoint will automatically run the seeders with `flask seed run`. If there are no seeders or they have already been applied, it skips without error. In other environments, seeders are skipped.

---



## 3. Environment Configuration

### PRE Environment

- Uses the database: `uvlhubdb`
- Environment file: `/home/pabolimor/trackhub-pre.env`
- Example execution:

    ```sh
    docker run -d \
      --name trackhub-pre \
      -p 5001:5000 \
      --env-file /home/pabolimor/trackhub-pre.env \
      -v /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro \
      --add-host=host.docker.internal:host-gateway \
      --restart always \
      trackhub-selfhosted:latest
    ```


### PROD Environment

- Database: `uvlhubdb_prod`
- Environment file: `/home/pabolimor/trackhub-prod.env`
- Example execution:

    ```sh
    docker run -d \
      --name trackhub-prod \
      -p 5002:5000 \
      --env-file /home/pabolimor/trackhub-prod.env \
      -v /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro \
      --add-host=host.docker.internal:host-gateway \
      --restart always \
      trackhub-selfhosted:latest
    ```

---



## 4. Cloudflare Tunnel

- Configuration: `/etc/cloudflared/config.yml`

    ```yaml
    ingress:
      - hostname: pre-trackhub.pabolimor.cloud
        service: http://localhost:5001
      - hostname: trackhub.pabolimor.cloud
        service: http://localhost:5002
      - service: http_status:404
    ```


- Restart the tunnel:

    ```sh
    sudo systemctl restart cloudflared
    ```

---




## 5. GitHub Actions: CD Self-Hosted

- Workflow: `.github/workflows/CD_selfhosted.yml`
- Two jobs: deploy-pre (on `trunk`), deploy-prod (on `main`)
- Uses the Docker build and run commands as above
- Requires a self-hosted runner on the server
- The `.env` files are **not** in the repository, only on the server

---


## 6. GitHub Actions Self-Hosted Runner

The runner is installed at `/home/pabolimor/actions-runner` and runs as a systemd service under the `pabolimor` user.

- Active service: `actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service`
- Managed with systemctl:
  ```sh
  sudo systemctl status actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service
  sudo systemctl restart actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service
  ```
- The runner is installed and configured following the official GitHub documentation:
  https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners
- Logs and diagnostics are found in `/home/pabolimor/actions-runner/_diag/`.
- The runner is prepared to execute jobs that require Docker and access to deployment files.

**Notes:**
- The runner is kept up to date using the scripts included in the `actions-runner` folder.
- If you need to run management commands manually, use `svc.sh` with sudo:
  ```sh
  cd ~/actions-runner
  sudo ./svc.sh status
  sudo ./svc.sh start
  sudo ./svc.sh stop
  ```

---

---



## 7. Deployment with Docker Compose

In addition to manual deployment with `docker run`, Docker Compose is used to manage TrackHub and Fakenodo services more easily and reproducibly.

The configuration files are located in `~/trackhub-deploy/`:

- `docker-compose.pre.yml`: PRE environment deployment
- `docker-compose.prod.yml`: PROD environment deployment
- `docker-compose.fakenodo.yml`: Fakenodo deployment
- `docker-compose.yml`: combined deployment of PRE, PROD, and Fakenodo

### Usage example

To start the PRE environment:
```sh
cd ~/trackhub-deploy
docker compose -f docker-compose.pre.yml up -d
```

To start the PROD environment:
```sh
cd ~/trackhub-deploy
docker compose -f docker-compose.prod.yml up -d
```

To start all services (PRE, PROD, and Fakenodo):
```sh
cd ~/trackhub-deploy
docker compose up -d
```

### Example docker-compose.pre.yml file
```yaml
services:
  trackhub-pre:
    image: trackhub-selfhosted:trunk
    container_name: trackhub-pre
    restart: always
    ports:
      - "5001:5000"
    env_file:
      - /home/pabolimor/trackhub-pre.env
    volumes:
      - /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro
      - ./storage-pre:/app/uploads
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Example docker-compose.prod.yml file
```yaml
services:
  trackhub-prod:
    image: trackhub-selfhosted:latest
    container_name: trackhub-prod
    restart: always
    ports:
      - "5002:5000"
    env_file:
      - /home/pabolimor/trackhub-prod.env
    volumes:
      - /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro
      - ./storage-prod:/app/uploads
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Example docker-compose.yml file (multi-service)
```yaml
version: "3.9"

services:
  trackhub-pre:
    image: trackhub-selfhosted:trunk
    container_name: trackhub-pre
    restart: always
    ports:
      - "5001:5000"
    env_file:
      - /home/pabolimor/trackhub-pre.env
    volumes:
      - /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"

  trackhub-prod:
    image: trackhub-selfhosted:latest
    container_name: trackhub-prod
    restart: always
    ports:
      - "5002:5000"
    env_file:
      - /home/pabolimor/trackhub-prod.env
    volumes:
      - /etc/mysql/ssl/ca.pem:/etc/ssl/certs/mariadb-ca.pem:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"

  fakenodo:
    image: fakenodo:latest
    container_name: fakenodo
    restart: always
    ports:
      - "5005:8000"
    environment:
      - PORT=8000
      - FAKENODO_FILES_DIR=/data
    volumes:
      - /srv/fakenodo/data:/data
```

---


## 8. Summary

- MariaDB with custom CA and TLS
- Docker image and entrypoint for self-hosted
- PRE/PROD environments on different ports and domains
- Cloudflare Tunnel for public access
- GitHub Actions for automated deployment
- Self-hosted runner managed as a systemd service
- Service deployment and management with Docker Compose

---


**Note:** Deployment on Render is not affected by this configuration.
