output "url" {
  description = "Public URL of the API and playground"
  value       = "http://${aws_lb.this.dns_name}"
}

output "ecr_repository" {
  value = aws_ecr_repository.api.repository_url
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_ROLE_ARN repository variable in GitHub"
  value       = aws_iam_role.github_deploy.arn
}
