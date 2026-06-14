terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source = "hashicorp/archive"
    }
  }
}

provider "aws" {
  region = var.aws_region
}


data "archive_file" "tickets_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambdas/tickets"
  output_path = "${path.module}/build/tickets_lambda.zip"
}

data "archive_file" "users_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambdas/users"
  output_path = "${path.module}/build/users_lambda.zip"
}


#
# VARIABLES
#

variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

#
# DYNAMODB TABLES
#

resource "aws_dynamodb_table" "tickets" {
  name         = "tickets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ticket_id"

  attribute {
    name = "ticket_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "users" {
  name         = "users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }
}

#
# IAM ROLE FOR LAMBDAS
#

resource "aws_iam_role" "lambda_role" {
  name = "ticket-system-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#
# DYNAMODB FULL ACCESS
#

resource "aws_iam_policy" "dynamodb_full_access" {
  name = "ticket-system-dynamodb-full-access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:*"
        ]
        Resource = [
          aws_dynamodb_table.tickets.arn,
          aws_dynamodb_table.users.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.dynamodb_full_access.arn
}

#
# LAMBDAS
#

resource "aws_lambda_function" "tickets_lambda" {
  function_name = "tickets-service"

  filename         = data.archive_file.tickets_zip.output_path
  source_code_hash = data.archive_file.tickets_zip.output_base64sha256

  role    = aws_iam_role.lambda_role.arn
  handler = "lambda_function.handler"
  runtime = "python3.12"

  environment {
    variables = {
      TICKETS_TABLE = aws_dynamodb_table.tickets.name
    }
  }
}

resource "aws_lambda_function" "users_lambda" {
  function_name = "users-service"

  filename         = data.archive_file.users_zip.output_path
  source_code_hash = data.archive_file.users_zip.output_base64sha256

  role    = aws_iam_role.lambda_role.arn
  handler = "lambda_function.handler"
  runtime = "python3.12"

  environment {
    variables = {
      USERS_TABLE = aws_dynamodb_table.users.name
    }
  }
}

#
# API GATEWAY HTTP API
#

resource "aws_apigatewayv2_api" "ticket_api" {
  name          = "ticket-management-api"
  protocol_type = "HTTP"
}

#
# INTEGRATIONS
#

resource "aws_apigatewayv2_integration" "tickets_integration" {
  api_id                 = aws_apigatewayv2_api.ticket_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.tickets_lambda.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "users_integration" {
  api_id                 = aws_apigatewayv2_api.ticket_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.users_lambda.invoke_arn
  payload_format_version = "2.0"
}

#
# ROUTES
#

resource "aws_apigatewayv2_route" "tickets_route" {
  api_id    = aws_apigatewayv2_api.ticket_api.id
  route_key = "ANY /tickets"
  target    = "integrations/${aws_apigatewayv2_integration.tickets_integration.id}"
}

resource "aws_apigatewayv2_route" "users_route" {
  api_id    = aws_apigatewayv2_api.ticket_api.id
  route_key = "ANY /users"
  target    = "integrations/${aws_apigatewayv2_integration.users_integration.id}"
}

#
# STAGE
#

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.ticket_api.id
  name        = "$default"
  auto_deploy = true
}

#
# LAMBDA PERMISSIONS
#

resource "aws_lambda_permission" "tickets_api_permission" {
  statement_id  = "AllowAPIGatewayInvokeTickets"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tickets_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.ticket_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "users_api_permission" {
  statement_id  = "AllowAPIGatewayInvokeUsers"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.users_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.ticket_api.execution_arn}/*/*"
}

#
# OUTPUTS
#

# output "api_endpoint" {
#  value = aws_apigatewayv2_api.ticket_api.api_endpoint
#}