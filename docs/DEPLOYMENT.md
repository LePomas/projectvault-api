# Deployment

ProjectVault keeps local development and production deployment separate. The API
can still run locally with Docker Compose and MinIO. The production CD workflow
is defined for precreated AWS resources and does not provision infrastructure.

## Current Deployment State

As of 2026-06-01, the live deployment setup is partial:

- Done: ECR repositories for the API and documents Lambda images.
- Done: production S3 bucket
  `projectvault-prod-lepomas-681742559054-us-east-1-an` with versioning, public
  access block, SSE-S3 encryption, and localhost CORS for initial testing.
- Done: IAM OIDC provider and `projectvault-github-deploy` trust policy for the
  GitHub `production` environment.
- Done: Secrets Manager secret `projectvault/prod/JWT_SECRET_KEY`.
- Pending: pushed ECR images.
- Pending: RDS PostgreSQL and `projectvault/prod/DATABASE_URL`.
- Pending: ECS cluster, service, and task definition.
- Pending: documents Lambda function and S3 ObjectCreated notification.
- Pending: deploy role permissions for ECR, ECS, Lambda, and `iam:PassRole`.
- Pending: first successful end-to-end GitHub Actions deploy.

## AWS Resources Expected By CD

Create or finish these resources before expecting the workflow to deploy
successfully:

- ECR repository for the API image.
- ECR repository for the documents Lambda image.
- ECS cluster, service, and task definition for the API container.
- Lambda function configured for image package type.
- RDS PostgreSQL database reachable from the ECS task and Lambda function.
- S3 bucket for document storage.
- S3 ObjectCreated notification that invokes the documents Lambda.
- IAM role for GitHub OIDC with permissions to push both ECR images, describe
  and deploy the ECS task definition, and update the Lambda function image.

The ECS task definition should already contain production-only values that do
not belong in GitHub, such as task roles, logging, networking, CPU/memory, and
secret references for `DATABASE_URL` and `JWT_SECRET_KEY`.

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
PROJECT_STORAGE_LIMIT_BYTES
S3_BUCKET
S3_REGION
```

`CORS_ALLOWED_ORIGINS` is a comma-separated list. In production it should be the
deployed frontend origin, for example `https://app.example.com`.

For the current production bucket, set:

```text
S3_BUCKET=projectvault-prod-lepomas-681742559054-us-east-1-an
```

## Deployment Flow

`.github/workflows/deploy.yml` runs on pushes to `main` and manual dispatches
after the workflow is pushed to GitHub:

1. Authenticate to AWS with GitHub OIDC.
2. Build and push the FastAPI image from `Dockerfile` to ECR.
3. Build and push the documents Lambda image from `Dockerfile.lambda` to ECR.
4. Download the current ECS task definition, render the new API image into it,
   and deploy it to the existing ECS service.
5. Update the documents Lambda function to the new Lambda image URI.

The workflow sets these runtime values for the API container:

```text
APP_ENV=production
DOCUMENT_STORAGE_BACKEND=s3
PUBLIC_REGISTRATION_ENABLED=false
S3_ENDPOINT_URL=
S3_PUBLIC_ENDPOINT_URL=
```

Blank S3 endpoint values make the storage adapter use AWS S3's default endpoint.

## Frontend Boundary

The frontend is intentionally optional. When added, keep it as a separate app
under `frontend/` with its own build, tests, and deployment path. The backend
must continue to run without the frontend folder or frontend assets.
