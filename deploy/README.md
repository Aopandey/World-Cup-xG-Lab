# World Cup xG Lab EC2 Deployment

This folder contains a simple production-style deployment for the Next.js + FastAPI dashboard on one AWS EC2 instance.

Streamlit is not deployed here. It was an early prototype for exploration. The production dashboard is served by Next.js, FastAPI, Nginx, and Docker Compose.

## Architecture

```text
Public HTTP :80
    |
    v
Nginx reverse proxy
    |-- /, /teams, /players, /model, /coverage -> Next.js frontend:3000
    |-- /api/* -> FastAPI backend:8000
    |-- /health and /api/health -> FastAPI /health
    |-- /static/* -> FastAPI static artifact assets
```

The backend serves precomputed JSON artifacts from `data/dashboard_artifacts/`. Models are not retrained when EC2 starts.

## Recommended EC2 Instance

For a portfolio deployment:

- Instance: `t3.medium` or `t3.small`
- OS: Ubuntu 24.04 LTS or Ubuntu 22.04 LTS
- Storage: 25-30 GB gp3
- Security group:
  - SSH `22` from your IP only
  - HTTP `80` from anywhere
  - HTTPS `443` from anywhere only if you add a domain/SSL later
  - Do not expose backend port `8000` publicly

Use `t3.medium` if you want smoother Docker builds on the EC2 box.

## Install Docker

On Ubuntu EC2:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Check:

```bash
docker --version
docker compose version
```

## Deploy

Clone the repo:

```bash
git clone https://github.com/Aopandey/World-Cup-xG-Lab.git
cd World-Cup-xG-Lab
```

Create the production env file:

```bash
cp deploy/.env.production.example deploy/.env.production
nano deploy/.env.production
```

Set:

```bash
BACKEND_ALLOWED_ORIGINS=http://YOUR_EC2_PUBLIC_IP
NEXT_PUBLIC_API_BASE_URL=/api
API_INTERNAL_BASE_URL=http://backend:8000
```

Build and start:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production up --build -d
```

Open:

```text
http://YOUR_EC2_PUBLIC_IP
```

## Logs

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production logs -f
```

## Stop

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production down
```

## Update Deployment

```bash
git pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production up --build -d
```

## Validate

From your local machine or from EC2:

```bash
python scripts/check_deployment_urls.py http://YOUR_EC2_PUBLIC_IP
```

The script checks:

- `/`
- `/api/teams`
- `/api/coverage`
- `/api/model/summary`
- `/health` or `/api/health`

## Optional S3 Backup

S3 can be added later as a backup location for `data/dashboard_artifacts/` and generated static assets.

For now, artifacts are shipped with the repo/backend image for simplicity. This keeps the portfolio deployment easy to understand and avoids making S3 required at runtime.
