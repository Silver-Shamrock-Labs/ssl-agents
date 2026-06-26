variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (e.g. prod, staging)"
  type        = string
  default     = "prod"
}

variable "slack_bot_token" {
  description = "Slack bot OAuth token (xoxb-...)"
  type        = string
  sensitive   = true
}

variable "slack_signing_secret" {
  description = "Slack app signing secret"
  type        = string
  sensitive   = true
}

variable "coding_routine_trigger_id" {
  description = "Trigger ID for the CODING routine API trigger"
  type        = string
}

variable "coding_routine_token" {
  description = "Bearer token for the CODING routine API trigger"
  type        = string
  sensitive   = true
}
