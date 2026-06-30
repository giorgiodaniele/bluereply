terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

#
# Create an S3 bucket
#
resource "aws_s3_bucket" "main" {
  bucket = "cloudability-cost-export-openai-bluereply"

  tags = {
    application   = "finops"
    owner         = "g.luppina@reply.it"
    environment   = "prod"
    business_unit = "BLUTIT_CA"
  }
}

#
# Block public access
#
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


data "aws_caller_identity" "current" {}

# Outputs
output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.main.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.main.arn
}

output "region" {
  description = "AWS region"
  value       = "eu-central-1"
}
