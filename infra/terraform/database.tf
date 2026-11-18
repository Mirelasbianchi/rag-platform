resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = var.project
  subnet_ids = data.aws_subnets.default.ids
}

# RDS for PostgreSQL 16 ships the pgvector extension; the app runs CREATE EXTENSION on boot.
resource "aws_db_instance" "this" {
  identifier              = var.project
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = 20
  storage_type            = "gp3"
  db_name                 = "rag"
  username                = "rag"
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  publicly_accessible     = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
}

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project}/database-url"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql://rag:%s@%s/rag?sslmode=require",
    random_password.db.result,
    aws_db_instance.this.endpoint,
  )
}
