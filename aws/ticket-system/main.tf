terraform {
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
  region = "eu-central-1"
}

#
# Generate a new DynamoDB table where tickets
# are going to be stored
#
resource "aws_dynamodb_table" "tickets" {
  name         = "tickets"
  hash_key     = "id"
  billing_mode = "PAY_PER_REQUEST"

  attribute {
    name = "id"
    type = "S"
  }
}

#
# Create a role assumed by Lambda functions
#
resource "aws_iam_role" "lambda_role" {
  name = "ticket-system-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

#
# Allow Lambda functions to write logs
# into CloudWatch
#
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#
# Allow Lambda functions to access DynamoDB resources
#
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

#
# Generate the deployment package for CreateTicket Lambda
#
data "archive_file" "create_ticket_zip" {
  type        = "zip"
  source_file = "${path.module}/lambdas/create_ticket/lambda_function.py"
  output_path = "${path.module}/create_ticket.zip"
}

#
# Generate the deployment package for CloseTicket Lambda
#
data "archive_file" "close_ticket_zip" {
  type        = "zip"
  source_file = "${path.module}/lambdas/close_ticket/lambda_function.py"
  output_path = "${path.module}/close_ticket.zip"
}

#
# Create a Lambda function responsible for creating new tickets
#
resource "aws_lambda_function" "create_ticket" {
  function_name    = "createTicket"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.13"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.create_ticket_zip.output_path
  source_code_hash = data.archive_file.create_ticket_zip.output_base64sha256
}

#
# Create a Lambda function responsible for closing open tickets
#
resource "aws_lambda_function" "close_ticket" {
  function_name    = "closeTicket"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.13"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.close_ticket_zip.output_path
  source_code_hash = data.archive_file.close_ticket_zip.output_base64sha256
}

#
# Create an HTTP API Gateway used to expose ticket operations
#
resource "aws_apigatewayv2_api" "ticket_api" {
  name          = "ticket-api"
  protocol_type = "HTTP"
}

#
# Connect POST /tickets requests to the CreateTicket Lambda
#
resource "aws_apigatewayv2_integration" "create_ticket" {
  api_id                 = aws_apigatewayv2_api.ticket_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_ticket.invoke_arn
  payload_format_version = "2.0"
}

#
# Register POST /tickets route
#
resource "aws_apigatewayv2_route" "create_ticket" {
  api_id    = aws_apigatewayv2_api.ticket_api.id
  route_key = "POST /tickets"
  target    = "integrations/${aws_apigatewayv2_integration.create_ticket.id}"
}

#
# Automatically deploy changes to the default stage
#
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.ticket_api.id
  name        = "$default"
  auto_deploy = true
}

#
# Allow API Gateway to invoke the CreateTicket Lambda
#
resource "aws_lambda_permission" "create_ticket_api" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_ticket.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ticket_api.execution_arn}/*/*"
}