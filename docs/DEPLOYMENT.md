# Deployment

World Cup xG Lab is deployed as a Docker Compose stack.

## Production Components

- Nginx reverse proxy.
- Next.js frontend.
- FastAPI backend.
- Precomputed dashboard JSON artifacts.

Streamlit is not deployed as the production app.

## Reverse Proxy Routing

```text
/        -> Next.js frontend
/api/*   -> FastAPI backend
/health  -> FastAPI health endpoint
/static/* -> FastAPI static assets
```

The backend container exposes port 8000 only inside the Docker network. Public users only access port 80 through Nginx.

## EC2 Runbook

The complete EC2 runbook lives in:

[../deploy/README.md](../deploy/README.md)

Core command:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production up --build -d
```

Validation:

```bash
python scripts/check_deployment_urls.py http://YOUR_EC2_PUBLIC_IP
```

## Environment Variables

```env
BACKEND_ALLOWED_ORIGINS=http://YOUR_EC2_PUBLIC_IP
NEXT_PUBLIC_API_BASE_URL=/api
API_INTERNAL_BASE_URL=http://backend:8000
```

`NEXT_PUBLIC_API_BASE_URL=/api` lets browser requests go through Nginx. `API_INTERNAL_BASE_URL=http://backend:8000` lets server-side Next.js requests use the Docker network.

## HTTPS

The current EC2 IP deployment is suitable for testing. For public sharing, use a domain and HTTPS.

Recommended future path:

- Point a domain or subdomain to the EC2 public IP.
- Add Caddy or Certbot-managed Nginx HTTPS.
- Redirect HTTP to HTTPS.
