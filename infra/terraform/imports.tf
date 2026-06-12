# ---------------------------------------------------------------------------
# One-time adoption of the existing (console-created) resources into Terraform
# state. These `import` blocks (Terraform >= 1.5) let `terraform plan` show what
# it will adopt and `terraform apply` bring them under management WITHOUT
# recreating them.
#
# After the first successful `apply`, DELETE this file — the resources are then
# tracked in state and these blocks are no longer needed.
#
# NOTE: aws_s3_bucket_notification is intentionally NOT imported here. The live
# bucket already has exactly the rule we declare, so the first apply will set it
# in place (it is an idempotent PUT of the whole notification config). If you
# prefer to import it too, add:
#   import { to = aws_s3_bucket_notification.documents, id = var.documents_bucket }
# ---------------------------------------------------------------------------

import {
  to = aws_iam_role.lambda
  id = "projectvault-documents-lambda"
}

import {
  to = aws_iam_role_policy_attachment.basic_execution
  id = "projectvault-documents-lambda/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

import {
  to = aws_iam_role_policy.access
  id = "projectvault-documents-lambda:ProjectVaultDocumentsLambdaAccess"
}

import {
  to = aws_lambda_function.documents
  id = "projectvault-documents"
}

import {
  to = aws_lambda_permission.allow_s3
  id = "projectvault-documents/AllowS3InvokeProjectVaultDocuments"
}
