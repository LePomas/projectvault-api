output "function_arn" {
  description = "ARN of the document-processing Lambda."
  value       = aws_lambda_function.documents.arn
}

output "role_arn" {
  description = "ARN of the Lambda execution role."
  value       = aws_iam_role.lambda.arn
}

output "image_uri" {
  description = "Container image the Lambda currently runs."
  value       = aws_lambda_function.documents.image_uri
}

output "trigger_bucket" {
  description = "Bucket whose ObjectCreated events invoke the Lambda."
  value       = var.documents_bucket
}
