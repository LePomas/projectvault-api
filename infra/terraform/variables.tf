variable "aws_region" {
  description = "AWS region the document-processing Lambda runs in."
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS account ID that owns the bucket and Lambda (used to scope the S3 invoke permission)."
  type        = string
  default     = "681742559054"
}

variable "function_name" {
  description = "Name of the S3-event Lambda function."
  type        = string
  default     = "projectvault-documents"
}

variable "image_uri" {
  description = <<-EOT
    Full ECR image URI (including tag) the Lambda runs. The tag is the git commit
    SHA the image was built from, e.g.
    681742559054.dkr.ecr.us-east-1.amazonaws.com/projectvault-documents-lambda:<sha>
  EOT
  type        = string
  default     = "681742559054.dkr.ecr.us-east-1.amazonaws.com/projectvault-documents-lambda:441e07ef27e03a09041a6b2d4b1ad875f564c6d4"
}

variable "documents_bucket" {
  description = "Existing S3 bucket whose ObjectCreated events trigger the Lambda. This config does NOT create the bucket."
  type        = string
  default     = "projectvault-prod-lepomas-681742559054-us-east-1-an"
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN holding the production DATABASE_URL the Lambda role may read."
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:681742559054:secret:projectvault/prod/DATABASE_URL-nlskB4"
}

variable "jwt_secret_key_secret_arn" {
  description = "Secrets Manager ARN holding the production JWT_SECRET_KEY the Lambda role may read."
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:681742559054:secret:projectvault/prod/JWT_SECRET_KEY-eaVqVT"
}

# Sensitive: the live Lambda stores DATABASE_URL as a PLAINTEXT env var. We model
# that faithfully here, but supply the value out-of-band (gitignored tfvars or a
# TF_VAR_database_url env var) so the connection string never lands in git.
# See README "Security follow-ups" for the recommended Secrets Manager migration.
variable "database_url" {
  description = "Plaintext DATABASE_URL injected as a Lambda env var (matches current live config). Supply via gitignored *.auto.tfvars or TF_VAR_database_url."
  type        = string
  sensitive   = true
}
