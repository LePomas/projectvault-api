# ProjectVault — Document Lambda (Terraform)

Infrastructure-as-code for the **S3 → Lambda** document-processing path. This was
originally created by hand in the AWS console; these files were reverse-engineered
from the live `us-east-1` account on **2026-06-11** so it is now reviewable and
reproducible.

## What this manages

| Resource | Terraform address | Live name |
|---|---|---|
| Lambda function (container image) | `aws_lambda_function.documents` | `projectvault-documents` |
| Execution role | `aws_iam_role.lambda` | `projectvault-documents-lambda` |
| Logs policy attachment | `aws_iam_role_policy_attachment.basic_execution` | `AWSLambdaBasicExecutionRole` |
| Inline S3+Secrets policy | `aws_iam_role_policy.access` | `ProjectVaultDocumentsLambdaAccess` |
| S3 → Lambda invoke permission | `aws_lambda_permission.allow_s3` | `AllowS3InvokeProjectVaultDocuments` |
| Bucket notification rule | `aws_s3_bucket_notification.documents` | `ProjectVaultDocumentsObjectCreated` |

**Not managed here** (pre-existing, referenced by name/URI): the S3 bucket
`projectvault-prod-…-an`, the ECR repository, and the Secrets Manager secrets.

## The flow (what the wiring does)

```
user uploads file ──▶ S3 bucket ──(s3:ObjectCreated:*)──▶ Lambda
                                                            └─ reads object, marks
                                                               the DB row "uploaded",
                                                               enforces the storage limit
```

## First-time use: adopt the existing infra (don't recreate it)

These resources already exist, so a plain `apply` would try to **create
duplicates and fail**. The included `imports.tf` adopts them into Terraform state
instead.

```bash
cd infra/terraform

# 1. Provide the one secret input (or set TF_VAR_database_url in your shell)
cp terraform.tfvars.example terraform.tfvars   # then edit; this file is gitignored

# 2. Initialise providers
terraform init

# 3. Review the adoption plan. Expect: 5 resources to import, ~0 changes.
#    A small diff on the bucket notification (it's set in-place) is normal.
terraform plan

# 4. Adopt + converge
terraform apply

# 5. Adoption is one-time — delete imports.tf and commit the rest.
rm imports.tf
```

> Consider configuring a remote backend (e.g. S3 + DynamoDB lock) before real
> team use. As written, state is local — fine for a first import, not for sharing.

## Day-2: deploying a new image

The image tag is the git SHA it was built from. To roll out a new build:

```bash
terraform apply -var="image_uri=<ecr-uri>:<new-sha>"
```

## Security follow-ups (surfaced while reverse-engineering this)

1. **Root access keys in use.** The local AWS CLI authenticates as the account
   `root` user. Create an IAM user/role with scoped permissions and delete the
   root access keys. (Unrelated to these files, but important.)
2. **`DATABASE_URL` is a plaintext Lambda env var.** Anyone with
   `lambda:GetFunctionConfiguration` can read the DB credentials. The role already
   has `secretsmanager:GetSecretValue` for `projectvault/prod/DATABASE_URL`, so the
   better pattern is to have the app fetch it at runtime and remove the env var
   (and the `database_url` Terraform variable with it).
3. **Config drift vs. the Radxa migration.** The repo/docs describe a self-hosted
   MinIO deployment, but this AWS Lambda + prod-bucket trigger is still live and was
   updated recently. Decide whether AWS prod is authoritative, the Radxa box is, or
   this is leftover to decommission.
