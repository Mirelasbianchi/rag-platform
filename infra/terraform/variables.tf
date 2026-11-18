variable "project" {
  description = "Name prefix for every resource"
  type        = string
  default     = "rag-platform"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_repository" {
  description = "owner/repo allowed to deploy through GitHub Actions OIDC"
  type        = string
  default     = "Mirelasbianchi/rag-platform"
}

variable "create_github_oidc_provider" {
  description = "Set to false if the account already has the token.actions.githubusercontent.com provider"
  type        = bool
  default     = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "task_cpu" {
  type    = number
  default = 256
}

variable "task_memory" {
  type    = number
  default = 512
}

variable "llm_model" {
  description = "Optional LiteLLM model for /ask. Empty keeps the offline extractive answers."
  type        = string
  default     = ""
}
