// Terraform variables
variable "STAGE" {
  type = string
  default = "LOCAL"
}

variable "lambda_logging_policy_arn" {
  type = string
}

variable "vsnandy_gw_id" {
  type = string
}

variable "vsnandy_user_pool_id" {
  type = string
}

variable "vsnandy_user_pool_client_id" {
  type = string
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

terraform {
  backend "s3" {
    bucket = "vsnandy-tfstate"
    key = "states"
    region = "us-east-1"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = "us-east-1"
}

// IMPORTS
import {
  to = aws_iam_policy.lambda_logging_policy
  id = "${var.lambda_logging_policy_arn}"
}

import {
  to = aws_dynamodb_table.terraform_state_lock
  id = "vsnandy-api-state"
}

import {
  to = aws_dynamodb_table.vsnandy_db
  id = "vsnandy_bets"
}

import {
  to = aws_s3_bucket.terraform_state
  id = "vsnandy-tfstate"
}

import {
  to = aws_iam_role.lambda_role
  id = "vsnandy_lambda_role"
}

import {
  to = aws_lambda_function.lambda_function
  id = "vsnandy-lambda-api"
}

import {
  to = aws_apigatewayv2_api.api
  id = "${var.vsnandy_gw_id}"
}

import {
  to = aws_lambda_permission.apigw
  id = "vsnandy-lambda-api/terraform-20241018154650326500000001"
}

import {
  to = aws_cognito_user_pool.pool
  id = "${var.vsnandy_user_pool_id}"
}

import {
  to = aws_cognito_user_pool_client.client
  id = "${var.vsnandy_user_pool_id}/${var.vsnandy_user_pool_client_id}"
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "vsnandy-tfstate"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
    bucket = aws_s3_bucket.terraform_state.id

    versioning_configuration {
      status = "Enabled"
    }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "vsnandy-api-state"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

// Define an IAM policy for the lambda
data "aws_iam_policy_document" "lambda_policy" { 
  statement {
    effect = "Allow"

    principals {
      type = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

// Define an IAM role for the lambda
// Assign the above policy as the assumed role for the lambda
resource "aws_iam_role" "lambda_role" {
  name = "vsnandy_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_policy.json
}

// IAM policy definitions
data "aws_iam_policy_document" "lambda_logging_policy_document" {
  // IAM policy for logging from the lambda
  statement {
    sid = "Logging"
    effect = "Allow"
    resources = ["arn:aws:logs:*:*:*"]
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
  }

  // IAM policy for lambda => dynamodb
  statement {
    sid = "DynamoDB"
    effect = "Allow"
    resources = [aws_dynamodb_table.vsnandy_db.arn]
    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchWriteItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem"
    ]
  }
}

// Create the logging_policy from the lambda_logging_policy
resource "aws_iam_policy" "lambda_logging_policy" {
  name = "vsnandy_lambda_logging_policy"
  description = "Lambda logging policy to Cloudwatch"
  policy = data.aws_iam_policy_document.lambda_logging_policy_document.json
  depends_on = [ aws_iam_role.lambda_role ]
}

// Attach lambda_logging_policy to the lambda_role
resource "aws_iam_role_policy_attachment" "attach_logging_policy_to_lambda_role" {
  role = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_logging_policy.arn
}

// Generate the lambda zip file from the src directory
// In Terraform ${path.module} is the current directory
data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = "${path.module}/src/"
  output_path = "${path.module}/src/vsnandy_lambda.zip"
}

// Create the lambda function
resource "aws_lambda_function" "lambda_function" {
  filename = "${path.module}/src/vsnandy_lambda.zip"
  function_name = "vsnandy-lambda-api"
  role = aws_iam_role.lambda_role.arn
  handler = "handler.handler"
  runtime = "python3.10"
  depends_on = [aws_iam_role_policy_attachment.attach_logging_policy_to_lambda_role]
}

// DynamoDB deployment
resource "aws_dynamodb_table" "vsnandy_db" {
  name           = "vsnandy_bets"
  billing_mode = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "Bettor"
  range_key      = "Week"

  attribute {
    name = "Bettor"
    type = "S"
  }

  attribute {
    name = "Week"
    type = "S"
  }
}

// COGNITO RESOURCES
resource "aws_cognito_user_pool" "pool" {
  name = "vsnandy-users"

  mfa_configuration = "ON"
  username_attributes = ["email"]
  deletion_protection = "ACTIVE"
  auto_verified_attributes = ["email"]
  tags = {}
  tags_all = {}
  account_recovery_setting {
    recovery_mechanism {
      name = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  password_policy {
    minimum_length = 8
    password_history_size = 0
    require_lowercase = true
    require_numbers = true
    require_symbols = true
    require_uppercase = true
    temporary_password_validity_days = 7
  }

  schema {
    attribute_data_type = "String"
    developer_only_attribute = false
    mutable = true
    name = "email"
    required = true
    string_attribute_constraints {
      max_length = "2048"
      min_length = "0"
    }
  }

  software_token_mfa_configuration {
    enabled = true
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  username_configuration {
    case_sensitive = false
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name = "website"
  user_pool_id = aws_cognito_user_pool.pool.id
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}

// API GATEWAY RESOURCES
# HTTP API
resource "aws_apigatewayv2_api" "api" {
  name = "vsnandy-api"
  protocol_type = "HTTP"
  target = aws_lambda_function.lambda_function.arn
}

# API GW Authorizer 
resource "aws_apigatewayv2_authorizer" "api_gw_auth" {
  name = "vsnandy_api_gw_cognito_authorizer"
  api_id = "${var.vsnandy_gw_id}"
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.client.id]
    issuer = "https://${aws_cognito_user_pool.pool.endpoint}"
  }
}

# Permission
resource "aws_lambda_permission" "apigw" {
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.arn
  principal = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

// OPTIONAL: Outputs for Terraform once the apply has completed

output "terraform_aws_role_output" {
  value = aws_iam_role.lambda_role.name
}

output "terraform_aws_role_arn_output" {
  value = aws_iam_role.lambda_role.arn
}

output "terraform_logging_arn_output" {
  value = aws_iam_policy.lambda_logging_policy.arn
}