# Deployment on Render

This guide covers the deployment process for Track Hub 1 on Render.

## Overview

Track Hub 1 uses two separate environments on Render:

| Environment | Branch | Trigger | Purpose |
|-------------|--------|---------|---------|
| Staging | `trunk` | Push to trunk | Pre-production testing |
| Production | `main` | Release created | Live application |

## Architecture

Each environment consists of:

- **Render Web Service**: Runs the Flask application from a Docker image
- **Docker Hub Image**: Built and pushed by GitHub Actions
- **External Database**: MariaDB hosted on Filess.io
- **Uploads Repository**: GitHub repo for persistent file storage

## Deployment Flow

### Staging

```
Push to trunk
    → GitHub Actions: Build Docker image
    → Push to Docker Hub (track-hub-1-staging)
    → Webhook triggers Render redeploy
    → Render pulls latest image and starts container
```

### Production

```
Push to main
    → GitHub Actions: Auto Release creates tag + changelog
    → GitHub Actions: Build Docker image with version tag
    → Push to Docker Hub (track-hub-1)
    → Webhook triggers Render redeploy
    → Render pulls latest image and starts container
```

## Environment Variables

Configure these in Render's dashboard for each environment:

### Required

| Variable | Description |
|----------|-------------|
| `DOMAIN` | Application domain |
| `FLASK_APP` | Flask application entry point |
| `FLASK_APP_NAME` | Display name for the application |
| `FLASK_ENV` | Environment mode |
| `SECRET_KEY` | Secret key for session encryption |
| `MARIADB_HOSTNAME` | Database host |
| `MARIADB_PORT` | Database port |
| `MARIADB_DATABASE` | Database name |
| `MARIADB_USER` | Database user |
| `MARIADB_PASSWORD` | Database password |
| `MARIADB_ROOT_PASSWORD` | Database root password |
| `WORKING_DIR` | Set the current dir |
| `UPLOADS_GIT_REPO_URL` | GitHub repo URL for uploads |
| `UPLOADS_GITHUB_TOKEN` | GitHub token for uploads sync |

### Staging Only

| Variable | Description |
|----------|-------------|
| `ENABLE_SEEDER` | Set to `true` to seed test data on empty database |

Note: Do not set `ENABLE_SEEDER` in production to avoid populating with test data.

## File Persistence

Render's filesystem is ephemeral. To persist uploaded files:

1. A GitHub repository stores the uploads (`track-hub-1-uploads-staging` or `track-hub-1-uploads`)
2. On container start, `sync_uploads.sh` clones the repo to `/app/uploads/`
3. A background watcher detects file changes and pushes them back to GitHub

## Troubleshooting

### Files not loading (404 errors)

- Check that the uploads repository contains the expected files
- Verify the database records match the file structure in the repo
- Check Render logs for sync errors

### Database issues

- Ensure the Filess.io database is accessible
- Verify environment variables are correctly set
- Check that migrations have run successfully

### Seeder not running (staging)

- Confirm `ENABLE_SEEDER=true` is set in environment variables
- The seeder only runs when the `user` table is empty
