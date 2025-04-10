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

variable "default_route_id" {
  type = string
}

/*
variable "options_route_id" {
  type = string
}
*/

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
  to = aws_dynamodb_table.wapit_db
  id = "wapit_draft"
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
  to = aws_lambda_function.auth_lambda_function
  id = "vsnandy-lambda-authorizer"
}

import {
  to = aws_apigatewayv2_api.api
  id = "${var.vsnandy_gw_id}"
}

/*
import {
  to = aws_lambda_permission.apigw
  id = "vsnandy-lambda-api/terraform-20241018154650326500000001"
}
*/

import {
  to = aws_cognito_user_pool.pool_v2
  id = "${var.vsnandy_user_pool_id}"
}

import {
  to = aws_cognito_user_pool_client.client
  id = "${var.vsnandy_user_pool_id}/${var.vsnandy_user_pool_client_id}"
}

import {
  to = aws_iam_role.lambda_authorizer_role
  id = "vsnandy_lambda_authorizer_role"
}

import {
  to = aws_apigatewayv2_integration.lambda
  id = "${var.vsnandy_gw_id}/${var.default_route_id}"
}

import {
  to = aws_apigatewayv2_route.default
  id = "${var.vsnandy_gw_id}/${var.default_route_id}"
}

import {
  to = aws_apigatewayv2_route.get_league
  id = "${var.vsnandy_gw_id}/zugc0vj"
}

import {
  to = aws_apigatewayv2_route.post_league
  id = "${var.vsnandy_gw_id}/ph2m39r"
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
    resources = [aws_dynamodb_table.vsnandy_db.arn, aws_dynamodb_table.wapit_db.arn]
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

  // IAM policy for lambda => cognito
  statement {
    sid = "Cognito"
    effect = "Allow"
    resources = [aws_cognito_user_pool.pool_v2.arn]
    actions = [
      "cognito-idp:ListUsersInGroup"
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
  timeout = 30 # Timeout in seconds, default is 3 seconds
  depends_on = [aws_iam_role_policy_attachment.attach_logging_policy_to_lambda_role]
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
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

resource "aws_dynamodb_table" "wapit_db" {
  name           = "wapit_draft"
  billing_mode   = "PROVISIONED"
  read_capacity = 1
  write_capacity = 1
  hash_key       = "LeagueID"
  range_key      = "PickNumber"

  attribute {
    name = "LeagueID"
    type = "S"
  }

  attribute {
    name = "PickNumber"
    type = "N"
  }

  attribute {
    name = "TeamID"
    type = "S"
  }

  # Global Secondary Index (GSI) to query by TeamID
  global_secondary_index {
    name               = "TeamPicksIndex"
    hash_key           = "TeamID"
    projection_type    = "ALL"
    read_capacity      = 1
    write_capacity     = 1
  }

  tags = {
    Name        = "wapit_draft"
    Environment = "prod"
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

# aws_cognito_user_pool.pool_v2:
resource "aws_cognito_user_pool" "pool_v2" {
    alias_attributes           = [
        "email",
        "phone_number",
    ]
    auto_verified_attributes   = [
        "email",
    ]
    custom_domain              = null
    deletion_protection        = "ACTIVE"
    email_verification_message = null
    email_verification_subject = null
    mfa_configuration          = "OFF"
    name                       = "vsnandy-user-pool-v2"
    sms_authentication_message = null
    sms_verification_message   = null
    tags                       = {}
    tags_all                   = {}

    account_recovery_setting {
        recovery_mechanism {
            name     = "verified_email"
            priority = 1
        }
        recovery_mechanism {
            name     = "verified_phone_number"
            priority = 2
        }
    }

    admin_create_user_config {
        allow_admin_create_user_only = false
    }

    email_configuration {
        configuration_set      = null
        email_sending_account  = "COGNITO_DEFAULT"
        from_email_address     = null
        reply_to_email_address = null
        source_arn             = null
    }

    password_policy {
        minimum_length                   = 8
        password_history_size            = 0
        require_lowercase                = true
        require_numbers                  = true
        require_symbols                  = true
        require_uppercase                = true
        temporary_password_validity_days = 7
    }

    schema {
        attribute_data_type      = "String"
        developer_only_attribute = false
        mutable                  = true
        name                     = "email"
        required                 = true

        string_attribute_constraints {
            max_length = "2048"
            min_length = "0"
        }
    }
    schema {
        attribute_data_type      = "String"
        developer_only_attribute = false
        mutable                  = true
        name                     = "name"
        required                 = true

        string_attribute_constraints {
            max_length = "2048"
            min_length = "0"
        }
    }
    schema {
        attribute_data_type      = "String"
        developer_only_attribute = false
        mutable                  = true
        name                     = "nickname"
        required                 = true

        string_attribute_constraints {
            max_length = "2048"
            min_length = "0"
        }
    }
    schema {
        attribute_data_type      = "String"
        developer_only_attribute = false
        mutable                  = true
        name                     = "phone_number"
        required                 = true

        string_attribute_constraints {
            max_length = "2048"
            min_length = "0"
        }
    }

    sms_configuration {
        external_id    = "eb0dba63-66ec-4538-a911-fbad1ba321f6"
        sns_caller_arn = "arn:aws:iam::918470975264:role/service-role/CognitoIdpSNSServiceRole"
        sns_region     = "us-east-1"
    }

    username_configuration {
        case_sensitive = false
    }

    verification_message_template {
        default_email_option  = "CONFIRM_WITH_CODE"
        email_message         = null
        email_message_by_link = null
        email_subject         = null
        email_subject_by_link = null
        sms_message           = null
    }
}

resource "aws_cognito_user_pool_client" "client" {
  name = "vsnandy.github.io"
  user_pool_id = aws_cognito_user_pool.pool_v2.id
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
  token_validity_units {
    access_token = "minutes"
    id_token = "minutes"
    refresh_token = "days"
  }
}

// API GATEWAY RESOURCES
# HTTP API
resource "aws_apigatewayv2_api" "api" {
  name = "vsnandy-api"
  protocol_type = "HTTP"
  target = aws_lambda_function.lambda_function.arn
  
  cors_configuration {
    allow_origins = ["http://localhost:3000", "http://localhost:9000", "https://vsnandy.github.io"]
    allow_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["Accept", "Content-Type", "Authorization"]
    allow_credentials = false
    max_age = 15
  }
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "get_league" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /ncaa/wapit/league/{league_id}/year/{year}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_league" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /ncaa/wapit/league/{league_id}/year/{year}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# API GW Authorizer 
resource "aws_apigatewayv2_authorizer" "api_gw_auth" {
  name = "vsnandy_api_gw_cognito_authorizer"
  api_id = "${var.vsnandy_gw_id}"
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.client.id]
    issuer = "https://${aws_cognito_user_pool.pool_v2.endpoint}"
  }
}


// Route definitions
resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"

  integration_method = "POST"
  integration_uri    = aws_lambda_function.lambda_function.arn
  payload_format_version = "2.0"
}


/*
resource "aws_apigatewayv2_route" "cors" {
  api_id = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
*/


/*
resource "aws_apigatewayv2_route" "cors" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "OPTIONS /{proxy+}"

  target = "integrations/${aws_apigatewayv2_integration.auth_integration.id}"
}
*/

// Define an IAM role for the lambda
// Assign the above policy as the assumed role for the lambda
resource "aws_iam_role" "lambda_authorizer_role" {
  name = "vsnandy_lambda_authorizer_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_policy.json
}
// Lambda CORS Authorizer
data "archive_file" "auth_lambda_zip" {
  type = "zip"
  source_dir = "${path.module}/src_auth/"
  output_path = "${path.module}/src_auth/vsnandy_lambda_authorizer.zip"
}

// Create the lambda function
resource "aws_lambda_function" "auth_lambda_function" {
  filename = "${path.module}/src_auth/vsnandy_lambda_authorizer.zip"
  function_name = "vsnandy-lambda-authorizer"
  role = aws_iam_role.lambda_authorizer_role.arn
  handler = "handler.handler"
  runtime = "python3.10"
}

/*
# API GW Routes
resource "aws_apigatewayv2_integration" "example" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "HTTP_PROXY"

  integration_method = ""
  integration_uri    = "https://example.com/{proxy}"
}

resource "aws_apigatewayv2_route" "example" {
  api_id    = aws_apigatewayv2_api.example.id
  route_key = "ANY /example/{proxy+}"

  target = "integrations/${aws_apigatewayv2_integration.example.id}"
}


resource "aws_api_gateway_stage" "gw_default_stage" {
  depends_on = [aws_cloudwatch_log_group.gw_default_log_group]
  stage_name = "$default"
}

resource "aws_cloudwatch_log_group" "gw_default_log_group" {
  name = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api.example.id}/$default"
  retention_in_days = 7
}
*/

/*
// API Gateway policy definitions
data "aws_iam_policy_document" "gw_logging_policy_document" {
  // IAM policy for logging from the api gateway
  statement {
    sid = "Logging"
    effect = "Allow"
    resources = ["arn:aws:logs:*:*:*"]
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:GetLogEvents",
      "logs:FilterLogEvents"
    ]
  }
}

// Create the logging_policy from the lambda_logging_policy
resource "aws_iam_policy" "gw_logging_policy" {
  name = "vsnandy_api_gw_logging_policy"
  description = "API Gateway logging policy to Cloudwatch"
  policy = data.aws_iam_policy_document.gw_logging_policy_document.json
  depends_on = [ aws_iam_role.lambda_role ]
}
*/

/*
resource "aws_apigatewayv2_integration" "api_gw_int" {
  api_id = aws_apigatewayv2_api.gateway.id
  integration_type = "AWS_PROXY"
  connection_type = "INTERNET"

}

# Add auth to API GW default path
resource "aws_apigatewayv2_route" "default_route" {
  api_id = aws_apigatewayv2_api.api.id
  route_key = "$default"

  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.api_gw_auth.id
}
*/

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