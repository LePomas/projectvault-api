# ---------------------------------------------------------------------------
# ProjectVault document-processing Lambda (S3 ObjectCreated -> mark uploaded)
#
# Reverse-engineered from the live us-east-1 account on 2026-06-11 so the
# previously console-clicked infrastructure is now version-controlled.
#
# This config MANAGES: the Lambda function, its IAM role + policies, the
# permission that lets S3 invoke it, and the bucket's notification rule.
# It does NOT manage: the S3 bucket itself or the ECR repository (both
# pre-exist and hold state/images). Those are referenced by name/URI.
#
# Adopting already-existing resources: see imports.tf and the README.
# ---------------------------------------------------------------------------

locals {
  bucket_arn = "arn:aws:s3:::${var.documents_bucket}"
}

# --- IAM role the Lambda assumes -------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# CloudWatch Logs write access (AWS-managed least-privilege policy for Lambda).
resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Narrow inline policy: read objects from the documents bucket and read exactly
# the two secrets this app needs. Nothing else. (Least privilege.)
resource "aws_iam_role_policy" "access" {
  name = "ProjectVaultDocumentsLambdaAccess"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${local.bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          var.database_url_secret_arn,
          var.jwt_secret_key_secret_arn,
        ]
      },
    ]
  })
}

# --- The function ----------------------------------------------------------

resource "aws_lambda_function" "documents" {
  function_name = var.function_name
  role          = aws_iam_role.lambda.arn

  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["x86_64"]

  timeout     = 60
  memory_size = 512

  environment {
    variables = {
      APP_ENV                     = "production"
      DOCUMENT_STORAGE_BACKEND    = "s3"
      S3_BUCKET                   = var.documents_bucket
      S3_REGION                   = var.aws_region
      S3_ENDPOINT_URL             = ""
      S3_PUBLIC_ENDPOINT_URL      = ""
      PROJECT_STORAGE_LIMIT_BYTES = "104857600"
      DATABASE_URL                = var.database_url
    }
  }
}

# --- Wiring: let S3 invoke the Lambda, then subscribe the bucket -----------

# The "phone number on the door": permit S3 (and ONLY this bucket, in ONLY this
# account) to invoke the function.
resource "aws_lambda_permission" "allow_s3" {
  statement_id   = "AllowS3InvokeProjectVaultDocuments"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.documents.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = local.bucket_arn
  source_account = var.account_id
}

# The "mailroom rule": on any object creation, buzz the Lambda.
resource "aws_s3_bucket_notification" "documents" {
  bucket = var.documents_bucket

  lambda_function {
    id                  = "ProjectVaultDocumentsObjectCreated"
    lambda_function_arn = aws_lambda_function.documents.arn
    events              = ["s3:ObjectCreated:*"]
  }

  # The permission must exist before S3 will accept the notification config.
  depends_on = [aws_lambda_permission.allow_s3]
}
