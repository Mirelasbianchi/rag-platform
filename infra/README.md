# Infrastructure

Planned AWS deployment:

- **Compute:** ECS Fargate service running the API container
- **Database:** RDS for PostgreSQL with the `vector` extension enabled
- **Images:** Amazon ECR, pushed by GitHub Actions on merge to `main`
- **Secrets:** AWS Secrets Manager for the database URL and API keys
- **Observability:** CloudWatch logs and metrics

Infrastructure as code (Terraform or AWS CDK) will live in this folder.
