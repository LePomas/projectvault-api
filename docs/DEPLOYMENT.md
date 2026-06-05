# Deployment

ProjectVault keeps local development and production deployment separate. The API
can still run locally with Docker Compose and MinIO. The production CD workflow
is defined for precreated AWS resources and does not provision infrastructure.

## Current Deployment State

As of 2026-06-01, the live deployment setup has completed the first internal
AWS deployment path:

- Done: ECR repositories for the API and documents Lambda images.
- Done: ECR images for the API and documents Lambda, including commit-SHA
  images pushed by GitHub Actions.
- Done: production S3 bucket
  `projectvault-prod-lepomas-681742559054-us-east-1-an` with versioning, public
  access block, SSE-S3 encryption, and localhost CORS for initial testing.
- Done: S3 ObjectCreated notification wired to `projectvault-documents`.
- Done: IAM OIDC provider and `projectvault-github-deploy` trust policy for the
  GitHub `production` environment.
- Done: deploy role permissions for ECR, ECS, Lambda, and `iam:PassRole`.
- Done: Secrets Manager secrets `projectvault/prod/JWT_SECRET_KEY` and
  `projectvault/prod/DATABASE_URL`.
- Done: private RDS PostgreSQL instance `projectvault-prod`.
- Done: ECS cluster `projectvault-prod`, service `projectvault-api`, and task
  definition `projectvault-api`.
- Done: image-based Lambda function `projectvault-documents`.
- Done: first successful backend/Lambda GitHub Actions Deploy workflow run.
- Planned for controlled demo review: HTTPS API ingress at `api.lepomas.xyz` through an
  Application Load Balancer restricted by source IP allowlist.
- Done: local controlled demo frontend under `frontend/`.
- Planned for frontend: static S3 and CloudFront hosting at
  `https://app.lepomas.xyz` with a DNS-only Cloudflare `CNAME`.
- Pending: production frontend AWS resources and Cloudflare DNS; CORS currently
  allows `http://localhost:3000`.
- Pending: infrastructure-as-code for AWS resources.
- Pending: app-level secret loading from Secrets Manager for Lambda. The current
  Lambda environment was manually configured with `DATABASE_URL` after function
  creation because the app expects environment variables at import time.

## AWS Resources Expected By CD

The CD workflow expects these resources to exist before it runs:

- ECR repository for the API image.
- ECR repository for the documents Lambda image.
- ECS cluster, service, and task definition for the API container.
- Lambda function configured for image package type.
- RDS PostgreSQL database reachable from the ECS task and Lambda function.
- S3 bucket for document storage.
- S3 ObjectCreated notification that invokes the documents Lambda.
- S3 bucket for frontend static assets.
- CloudFront distribution for the frontend with `app.lepomas.xyz` as an
  alternate domain name.
- ACM certificate covering `app.lepomas.xyz` in `us-east-1` for CloudFront.
- IAM role for GitHub OIDC with permissions to push both ECR images, describe
  and deploy the ECS task definition, update the Lambda function image, upload
  frontend assets to S3, and create CloudFront invalidations.

The ECS task definition contains production-only values that do not belong in
GitHub, such as task roles, logging, networking, CPU/memory, and secret
references for `DATABASE_URL` and `JWT_SECRET_KEY`.

## GitHub Production Variables

Set these as GitHub environment variables for the `production` environment:

```text
AWS_REGION
AWS_ROLE_TO_ASSUME
API_ECR_REPOSITORY
LAMBDA_ECR_REPOSITORY
ECS_CLUSTER
ECS_SERVICE
ECS_TASK_DEFINITION
ECS_CONTAINER_NAME
LAMBDA_FUNCTION_NAME
CORS_ALLOWED_ORIGINS
PUBLIC_REGISTRATION_ENABLED
PROJECT_STORAGE_LIMIT_BYTES
S3_BUCKET
S3_REGION
FRONTEND_S3_BUCKET
FRONTEND_CLOUDFRONT_DISTRIBUTION_ID
VITE_PROJECTVAULT_API_BASE_URL
```

`CORS_ALLOWED_ORIGINS` is a comma-separated list. It is currently set to
`http://localhost:3000` for initial testing. For the frontend cutover, set it to
`http://localhost:3000,https://app.lepomas.xyz`.

Set:

```text
VITE_PROJECTVAULT_API_BASE_URL=https://api.lepomas.xyz
```

`PUBLIC_REGISTRATION_ENABLED` defaults to `false` in the deployment workflow
when the GitHub variable is not set. For the controlled demo environment, set
it to `true` only after HTTPS ingress is restricted to the approved source IPs.

For the current production bucket, set:

```text
S3_BUCKET=projectvault-prod-lepomas-681742559054-us-east-1-an
```

## Deployment Flow

`.github/workflows/deploy.yml` runs on pushes to `main` and manual dispatches:

1. Authenticate to AWS with GitHub OIDC.
2. Build and push the FastAPI image from `Dockerfile` to ECR.
3. Build and push the documents Lambda image from `Dockerfile.lambda` to ECR.
4. Download the current ECS task definition, render the new API image into it,
   and deploy it to the existing ECS service.
5. Update the documents Lambda function to the new Lambda image URI.
6. Install frontend dependencies, run the frontend checks, build the Vite app,
   upload `frontend/dist` to the frontend S3 bucket, and invalidate CloudFront.

The workflow sets these runtime values for the API container:

```text
APP_ENV=production
DOCUMENT_STORAGE_BACKEND=s3
PUBLIC_REGISTRATION_ENABLED=${{ vars.PUBLIC_REGISTRATION_ENABLED || 'false' }}
S3_ENDPOINT_URL=
S3_PUBLIC_ENDPOINT_URL=
```

Blank S3 endpoint values make the storage adapter use AWS S3's default endpoint.

## Frontend Boundary

The frontend is intentionally optional and lives as a separate Vite app under
`frontend/`. The backend must continue to run without the frontend folder or
frontend assets.

Local review commands:

```bash
cd frontend
npm install
npm run dev
```

The local app runs on `http://localhost:3000` and reads
`VITE_PROJECTVAULT_API_BASE_URL`, defaulting to `https://api.lepomas.xyz`.

When the frontend is deployed publicly, use `https://app.lepomas.xyz` and set
the backend production `CORS_ALLOWED_ORIGINS` to include both
`http://localhost:3000` and `https://app.lepomas.xyz`.

Frontend Docker/container hosting is intentionally not used. The Vite app is
static, so the selected production path is S3 plus CloudFront.

## Frontend DNS And Cutover

Prepare these resources before the first frontend deploy workflow run:

1. Create a private S3 bucket for the Vite build output with public access
   blocked.
2. Create a CloudFront distribution backed by that bucket, preferably through
   origin access control.
3. Request or attach an ACM certificate in `us-east-1` covering
   `app.lepomas.xyz`.
4. Add the ACM DNS validation CNAME in Cloudflare.
5. Add `app.lepomas.xyz` as a CloudFront alternate domain name.
6. Add a Cloudflare DNS-only `CNAME`:
   - Name: `app`
   - Target: the CloudFront distribution domain, for example
     `dxxxxx.cloudfront.net`
   - Proxy status: DNS only
   - TTL: Auto
7. Set the GitHub production variables `FRONTEND_S3_BUCKET`,
   `FRONTEND_CLOUDFRONT_DISTRIBUTION_ID`,
   `VITE_PROJECTVAULT_API_BASE_URL=https://api.lepomas.xyz`, and
   `CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.lepomas.xyz`.
8. Run one controlled Deploy workflow cutover, then verify
   `https://app.lepomas.xyz` and browser CORS against `https://api.lepomas.xyz`.

## Controlled Demo Ingress

Expose the live API for review with a dedicated HTTPS hostname and network-level
allowlist:

1. Request an ACM certificate for `api.lepomas.xyz` in the same region as the
   ALB.
2. Add the ACM DNS validation record in Cloudflare.
3. Create an internet-facing Application Load Balancer with an HTTPS listener
   for the certificate and a target group for the existing ECS service.
4. Allow inbound `443` on the ALB security group only from the reviewer public
   IP/CIDR and the owner public IP/CIDR.
5. Allow inbound API traffic on the ECS task security group only from the ALB
   security group.
6. Add a DNS-only Cloudflare `CNAME` for `api.lepomas.xyz` pointing to the ALB
   DNS name. Do not proxy this record, because the AWS security group must see
   the real client source IP.
7. Set the GitHub production variable
   `PUBLIC_REGISTRATION_ENABLED=true`, then run the Deploy workflow.

Review smoke checks from an allowed source IP:

```bash
curl https://api.lepomas.xyz/health
curl -X POST https://api.lepomas.xyz/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"login":"demo-reviewer","email":"demo-reviewer@example.com","password":"super-secret-123","repeat_password":"super-secret-123"}'
curl -X POST https://api.lepomas.xyz/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"demo-reviewer","password":"super-secret-123"}'
```

From a non-allowed source IP, the API should be unreachable before FastAPI
handles the request.
