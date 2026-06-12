# Deployment

ProjectVault keeps local development and production deployment separate. The API
runs locally with Docker Compose and MinIO, and is deployed to a **self-hosted
Radxa Zero 3E (ARM64) server** via an SSH-based GitHub Actions workflow.

> History: through 2026-06-01 the project targeted an AWS path (ECS/ECR/Lambda/
> S3/RDS/CloudFront). On 2026-06-09 deployment was migrated to a self-hosted
> stack to remove cloud cost and exercise a full self-managed runtime. The AWS
> design is retained for reference at the end of this document; the Lambda image
> (`Dockerfile.lambda`) and `app/lambda_handlers/s3_events.py` remain in the repo
> as the S3 event-finalization code path but are not deployed in the self-hosted
> setup.

## Current Deployment State (self-hosted)

As of 2026-06-09 the live deployment is a Docker Compose stack on the Radxa
server:

- **API**: FastAPI container built from `Dockerfile`, served on the internal
  Docker network (no host port published in production).
- **PostgreSQL 16**: `db` service, bootstrapped from `db/init/`.
- **MinIO**: S3-compatible object storage replacing AWS S3 for documents.
  Internal endpoint `http://minio:9000`; public endpoint
  `https://storage.lepomas.xyz`.
- **Caddy** (`caddy:2-alpine`): reverse proxy that routes **plain HTTP** by
  `Host` header inside the Docker network (no host ports). It serves the static
  frontend from `./frontend/dist` and proxies `api.*` and `storage.*`.
- **cloudflared**: Cloudflare Tunnel that terminates TLS at Cloudflare's edge and
  forwards all three hostnames to Caddy. **No inbound ports** are opened on the
  server, which works behind CGNAT.

### Hostnames

| Hostname              | Routed to        | Purpose                       |
| --------------------- | ---------------- | ----------------------------- |
| `api.lepomas.xyz`     | `api:8000`       | FastAPI backend               |
| `app.lepomas.xyz`     | `/srv/frontend`  | Static Vite frontend (Caddy)  |
| `storage.lepomas.xyz` | `minio:9000`     | MinIO presigned document URLs |

### Edge and tunnel

```text
Browser ──HTTPS──▶ Cloudflare edge ──Tunnel──▶ cloudflared ──HTTP──▶ Caddy ──▶ api / minio / frontend
```

- `cloudflared` authenticates with `TUNNEL_TOKEN` (the `CLOUDFLARE_TUNNEL_TOKEN`
  env var). The token is a UUID-style secret, not raw credential bytes, so
  file-based `credentials.json` is **not** used for auth.
- `cloudflared/config.yml` defines local ingress rules so the tunnel ignores any
  remote dashboard-managed configuration and routes every hostname to
  `http://caddy:80`.
- Caddy does **not** publish host ports; only `cloudflared` (egress) talks to it.

## Compose Files

Production layers `docker-compose.prod.yml` over the base `docker-compose.yml`:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production override sets, for the API container:

```text
APP_ENV=production
DOCUMENT_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_PUBLIC_ENDPOINT_URL=https://storage.lepomas.xyz
CORS_ALLOWED_ORIGINS=https://app.lepomas.xyz
PUBLIC_REGISTRATION_ENABLED=false
```

It also adds the `caddy` and `cloudflared` services and removes published host
ports from `caddy`.

## Server Secrets

Kept on the server only (not in git, not in GitHub):

- `.env` — `DATABASE_URL`, `JWT_SECRET_KEY`, `CLOUDFLARE_TUNNEL_TOKEN`, MinIO
  credentials, etc.
- `cloudflared/credentials.json` — gitignored (only `cloudflared/config.yml` is
  tracked).

## Backend Deploy Workflow

`.github/workflows/deploy.yml` ("Deploy Backend") runs on pushes to `main`
(ignoring `docs/**`, `README.md`, `AGENTS.md`, and `frontend/**`) and on manual
dispatch:

1. Load `DEPLOY_SSH_KEY` and `ssh-keyscan` the `DEPLOY_HOST`.
2. `rsync -az --delete` the repo to `DEPLOY_PATH` on the server, excluding
   `.git`, `.venv`, caches, `.env`, `storage/`, and frontend node/dist artifacts.
3. Over SSH: `docker compose` build + `up -d` with both compose files, then
   `docker image prune -f`.

Required GitHub `production` secrets: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`,
`DEPLOY_USER`, `DEPLOY_PATH`.

## Frontend Deploy Workflow

`.github/workflows/deploy-frontend.yml` ("Deploy Frontend") runs on pushes to
`main` that change `frontend/**`, and on manual dispatch:

1. `npm ci`, `npm test`, `npm run typecheck`, `npm run build` (with
   `VITE_PROJECTVAULT_API_BASE_URL=https://api.lepomas.xyz`).
2. `rsync` `frontend/dist/` to `DEPLOY_PATH/frontend/dist/` on the server, where
   Caddy serves it for `app.lepomas.xyz`.

No S3 upload or CloudFront invalidation is involved anymore.

## Frontend Boundary

The frontend is an optional, separate Vite app under `frontend/`. The backend
must run without the frontend folder or assets. Local review:

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

The local app reads `VITE_PROJECTVAULT_API_BASE_URL` (default
`https://api.lepomas.xyz`).

## Review Smoke Checks

```bash
curl https://api.lepomas.xyz/health
curl -X POST https://api.lepomas.xyz/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"demo-reviewer","password":"super-secret-123"}'
```

`PUBLIC_REGISTRATION_ENABLED` is `false` in production; create demo accounts via
the seed script or by temporarily enabling registration.

---

## Appendix: Previous AWS Architecture (historical / reference)

The following describes the AWS path used before the self-hosted migration. It is
kept for study and in case a cloud path is revisited. It is **not** the current
deployment.

The AWS CD workflow expected these precreated resources:

- ECR repositories for the API image and the documents Lambda image.
- ECS cluster, service, and task definition for the API container.
- Lambda function (image package type) for `app.lambda_handlers.s3_events`.
- RDS PostgreSQL reachable from the ECS task and Lambda.
- S3 bucket for document storage with an `ObjectCreated` notification invoking
  the documents Lambda.
- S3 bucket + CloudFront distribution for the static frontend
  (`app.lepomas.xyz`), with an ACM cert in `us-east-1`.
- IAM role for GitHub OIDC able to push ECR images, deploy the ECS task
  definition, update the Lambda image, sync frontend assets to S3, and create
  CloudFront invalidations.
- Secrets Manager secrets for `DATABASE_URL` and `JWT_SECRET_KEY`.
- An internet-facing ALB with an HTTPS listener (`api.lepomas.xyz`) restricted by
  source-IP allowlist for controlled demo ingress.

AWS deploy flow (superseded): authenticate via GitHub OIDC → push API and Lambda
images to ECR → render the ECS task definition with the new image and
`DOCUMENT_STORAGE_BACKEND=s3` (blank `S3_ENDPOINT_URL` to use AWS S3 defaults) →
deploy to ECS → update the documents Lambda image. The frontend deployed via
`aws s3 sync` plus a CloudFront invalidation.
