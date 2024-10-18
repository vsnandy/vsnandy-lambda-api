// Terraform variables
variable "STAGE" {
  type = string
  default = "LOCAL"
}

variable "lambda_logging_policy_arn" {
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
  to = aws_lambda_function_url.lambda_url
  id = "vsnandy-lambda-api"
}

import {
  to = aws_iam_role.vsnandy-admin-role
  id = "vsnandy-admin-role"
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

// Lambda Function URL
resource "aws_lambda_function_url" "lambda_url" {
  function_name      = aws_lambda_function.lambda_function.arn
  authorization_type = "AWS_IAM"

  cors {
    allow_credentials = true
    allow_origins = ["http://localhost:3000", "https://vsnandy.github.io"]
    allow_methods = ["*"]
    allow_headers = ["date", "keep-alive"]
    expose_headers = ["keep-alive", "date"]
    max_age = 86400
  } 
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

// IAM policy document for lambda function url access
data "aws_iam_policy_document" "lambda_function_url_access_policy_doc" {
  statement {
    sid = "IAMRole"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunctionUrl"
    ]
    resources = [aws_lambda_function_url.lambda_url.function_arn]
  }
}

// Policy for calling lambda function url
resource "aws_iam_policy" "lambda_function_url_access_policy" {
  name = "vsnandy_lambda_api_function_url_access_policy"
  description = "IAM policy to access vsnandy lambda api function url. Will be attached to the lambda_function_url_access_role."
  policy = data.aws_iam_policy_document.lambda_function_url_access_policy_doc.json
}

// Define an IAM policy for the lambda
data "aws_iam_policy_document" "vsnandy-admin-policy" { 
  statement {
    effect = "Allow"

    principals {
      type = "Federated"
      identifiers = ["cognito-identity.amazonaws.com"]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test = "StringEquals"
      variable = "cognito-identity.amazonaws.com:aud"
      values = ["us-east-1:ca640fd6-c0c7-46b8-a721-9dd4ff004ddf"]
    }

    condition {
      test = "ForAnyValue:StringLike"
      variable = "cognito-identity.amazonaws.com:amr"
      values = ["authenticated"]
    }
  }
}

// Define an IAM role for the lambda
// Assign the above policy as the assumed role for the lambda
resource "aws_iam_role" "vsnandy-admin-role" {
  name = "vsnandy-admin-role"
  path = "/service-role/"
  assume_role_policy = data.aws_iam_policy_document.vsnandy-admin-policy.json
}

// Attach lambda_logging_policy to the lambda_role
resource "aws_iam_role_policy_attachment" "attach_lambda_function_url_policy" {
  role = aws_iam_role.vsnandy-admin-role.name
  policy_arn = aws_iam_policy.lambda_function_url_access_policy.arn
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


///////////////////////////
///////////////////////////
///////////////////////////
///////////////////////////

/*
variable "STAGE" {
  type    = string
  default = "local"
}

provider "aws" {
  alias = "localstack"
  region = "us-east-1"  # You can set this to any AWS region

  // Skip AWS credentials validation if we're running locally
  skip_credentials_validation = var.STAGE == "local"
  skip_metadata_api_check     = var.STAGE == "local"
  skip_requesting_account_id  = var.STAGE == "local"

  // You can use these fake keys for local AWS testing
  access_key = var.STAGE == "local" ? "testKey" : "realKeyForProduction"
  secret_key = var.STAGE == "local" ? "testSecret" : "realSecretForProduction"

  endpoints {
    dynamodb   = var.STAGE == "local" ? "http://localhost:4566" : null
    lambda     = var.STAGE == "local" ? "http://localhost:4574" : null
    cloudwatch = var.STAGE == "local" ? "http://localhost:4582" : null
    iam        = var.STAGE == "local" ? "http://localhost:4593" : null
  }
}

terraform {
  backend "s3" {
    bucket = "vsnandy-lambda"
    key    = "tfstate/terraform.tfstate"
    region = "us-east-1"
  }
}


resource "aws_s3_bucket" "terraform_state" {
  bucket = "vsnandy-lambda"

  # Prevent accidental deletion of this S3 bucket
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_dynamodb_table" "bets_table" {
  provider = aws.localstack  # Use the LocalStack-specific provider alias
  name           = "bets"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "name"
  range_key      = "week"

  attribute {
    name = "name"
    type = "S"
  }

  attribute {
    name = "week"
    type = "S"
  }
}

data "aws_iam_policy_document" "assume_role" { 
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "vsnandy_lambda_role" {
  name               = "vsnandy_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "../lambda/src/handler.py"
  output_path = "../lambda/src/build/lambda.zip"
}

resource "aws_lambda_function" "vsnandy_lambda" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = "../lambda/src/build/lambda.zip"
  function_name = "vsnandy_lambda"
  role          = aws_iam_role.vsnandy_lambda_role.arn
  handler       = "handler.handler"
  timeout       = 300

  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime = "python3.8"
}

resource "aws_cloudwatch_log_group" "vsnandy_lambda_loggroup" {
  name              = "/aws/lambda/${aws_lambda_function.vsnandy_lambda.function_name}"
  retention_in_days = 3
}

data "aws_iam_policy_document" "vsnandy_lambda_policy" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      aws_cloudwatch_log_group.vsnandy_lambda_loggroup.arn,
      "${aws_cloudwatch_log_group.vsnandy_lambda_loggroup.arn}:*"
    ]
  }
}

resource "aws_iam_role_policy" "vsnandy_lambda_role_policy" {
  policy = data.aws_iam_policy_document.vsnandy_lambda_policy.json
  role   = aws_iam_role.vsnandy_lambda_role.id
  name   = "vsnandy-lambda-policy"
}

resource "aws_lambda_function_url" "vsnandy_lambda_function_url" {
  function_name      = aws_lambda_function.vsnandy_lambda.id
  authorization_type = "NONE"
  cors {
    allow_origins = ["*"]
  }
}
*/