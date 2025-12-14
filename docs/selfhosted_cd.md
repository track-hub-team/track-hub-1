
---

# Guía de Despliegue Self-Hosted (Proxmox)

## Especificaciones del Servidor

El entorno de ejecución utiliza el siguiente hardware:

- **CPU:** AMD Ryzen 5 5650G
- **RAM:** 32 GB
- **Almacenamiento:**
  - Mirror de SSD de 250 GB (RAID 1) para el sistema y datos críticos
  - NVMe de 300 GB dedicado para la aplicación y sus volúmenes

Esto garantiza alto rendimiento, redundancia y espacio suficiente para los servicios y cargas de trabajo de TrackHub.


## Resumen

Este documento describe cómo desplegar TrackHub en un servidor Proxmox autogestionado (self-hosted) con MariaDB (TLS), dos entornos (PRE/PROD), contenedores Docker, Cloudflare Tunnel y despliegue automatizado mediante GitHub Actions.

- Los despliegues automáticos se disparan en los pushes a las ramas `trunk` (PRE) y `main` (PROD).
- El runner self-hosted ejecuta los jobs definidos en `.github/workflows/CD_selfhosted.yml`.
- El pipeline realiza:
  1. Checkout del código
  2. Build de la imagen Docker
  3. Despliegue del contenedor (o stack Docker Compose)
  4. (Opcional) Ejecución de tests/linting antes del despliegue
- El estado del pipeline puede monitorizarse desde la pestaña Actions del repositorio en GitHub.

---


## 1. Configuración TLS en MariaDB

**En el host donde corre MariaDB (no en el contenedor):**

1. Crear el directorio SSL y la CA.
2. Generar la clave del servidor y el CSR para `host.docker.internal`.
3. Firmar el certificado del servidor con tu CA.
4. Configurar MariaDB (`/etc/mysql/mariadb.conf.d/50-server.cnf`):

  ```
  [mysqld]
  ssl-ca=/etc/mysql/ssl/ca.pem
  ssl-cert=/etc/mysql/ssl/server-cert.pem
  ssl-key=/etc/mysql/ssl/server-key.pem
  # require_secure_transport=ON (opcional)
  ```

5. Reiniciar MariaDB y verificar con:

  ```
  sudo mariadb -e "SHOW VARIABLES LIKE 'have_ssl';"
  ```

---



## 2. Imagen Docker para Self-Hosted

- Dockerfile: `docker/images/Dockerfile.selfhosted`
- Entrypoint: `docker/entrypoints/selfhosted_entrypoint.sh`
- Características principales:
  - Espera a que MariaDB esté disponible (con TLS si se define `MARIADB_SSL_CA`)
  - Ejecuta migraciones Alembic
  - **Ejecuta seeders automáticamente si detecta entorno de preproducción**
  - Arranca Gunicorn

**Nota sobre seeders:**
Si la variable de entorno `FLASK_ENV` es `preproduction` o `ENV` es `pre`, el entrypoint ejecutará automáticamente los seeders con `flask seed run`. Si no hay seeders o ya se aplicaron, lo omite sin error. En otros entornos, los seeders se saltan.

---


## 3. Configuración de Entornos

### Entorno PRE

- Usa la base de datos: `uvlhubdb`
- Archivo de entorno: `/home/pabolimor/trackhub-pre.env`
- Ejemplo de ejecución:

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

### Entorno PROD

- Base de datos: `uvlhubdb_prod`
- Archivo de entorno: `/home/pabolimor/trackhub-prod.env`
- Ejemplo de ejecución:

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

- Configuración: `/etc/cloudflared/config.yml`

    ```yaml
    ingress:
      - hostname: pre-trackhub.pabolimor.cloud
        service: http://localhost:5001
      - hostname: trackhub.pabolimor.cloud
        service: http://localhost:5002
      - service: http_status:404
    ```

- Reiniciar el túnel:

    ```sh
    sudo systemctl restart cloudflared
    ```

---



## 5. GitHub Actions: CD Self-Hosted

- Workflow: `.github/workflows/CD_selfhosted.yml`
- Dos jobs: deploy-pre (en `trunk`), deploy-prod (en `main`)
- Usa los comandos de build y run de Docker como arriba
- Requiere un runner self-hosted en el servidor
- Los archivos `.env` **no** están en el repositorio, solo en el servidor

---

## 6. Runner Self-Hosted de GitHub Actions

El runner está instalado en `/home/pabolimor/actions-runner` y corre como servicio systemd bajo el usuario `pabolimor`.

- Servicio activo: `actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service`
- Se gestiona con systemctl:
  ```sh
  sudo systemctl status actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service
  sudo systemctl restart actions.runner.track-hub-team-track-hub-1.trackhub-server-deploy.service
  ```
- El runner se instala y configura siguiendo la documentación oficial de GitHub:
  https://docs.github.com/es/actions/hosting-your-own-runners/adding-self-hosted-runners
- Los logs y diagnósticos se encuentran en `/home/pabolimor/actions-runner/_diag/`.
- El runner está preparado para ejecutar jobs que requieren Docker y acceso a los archivos de despliegue.

**Notas:**
- El runner se mantiene actualizado usando los scripts incluidos en la carpeta `actions-runner`.
- Si se requiere ejecutar comandos de gestión manualmente, usar `svc.sh` con sudo:
  ```sh
  cd ~/actions-runner
  sudo ./svc.sh status
  sudo ./svc.sh start
  sudo ./svc.sh stop
  ```

---

---



## 7. Despliegue con Docker Compose

Además del despliegue manual con `docker run`, se utiliza Docker Compose para gestionar los servicios de TrackHub y Fakenodo de forma más sencilla y reproducible.

Los archivos de configuración se encuentran en `~/trackhub-deploy/`:

- `docker-compose.pre.yml`: despliegue del entorno PRE
- `docker-compose.prod.yml`: despliegue del entorno PROD
- `docker-compose.fakenodo.yml`: despliegue de Fakenodo
- `docker-compose.yml`: despliegue combinado de PRE, PROD y Fakenodo

### Ejemplo de uso

Para levantar el entorno PRE:
```sh
cd ~/trackhub-deploy
docker compose -f docker-compose.pre.yml up -d
```

Para levantar el entorno PROD:
```sh
cd ~/trackhub-deploy
docker compose -f docker-compose.prod.yml up -d
```

Para levantar todos los servicios (PRE, PROD y Fakenodo):
```sh
cd ~/trackhub-deploy
docker compose up -d
```

### Ejemplo de archivo docker-compose.pre.yml
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

### Ejemplo de archivo docker-compose.prod.yml
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

### Ejemplo de archivo docker-compose.yml (multi-servicio)
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

## 8. Resumen

- MariaDB con CA propia y TLS
- Imagen Docker y entrypoint para self-hosted
- Entornos PRE/PROD en diferentes puertos y dominios
- Cloudflare Tunnel para acceso público
- GitHub Actions para despliegue automatizado
- Runner self-hosted gestionado como servicio systemd
- Despliegue y gestión de servicios con Docker Compose

---

**Nota:** El despliegue en Render no se ve afectado por esta configuración.
