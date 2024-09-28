// Terraform variables
variable "STAGE" {
  type = string
  default = "LOCAL"
}

variable "lambda_logging_policy_arn" {}

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
  id = var.lambda_logging_policy_arn
}

import {
  to = aws_dynamodb_table.terraform-state-lock
  id = "vsnandy-api-state"
}

import {
  to = aws_s3_bucket.terraform-state
  id = "vsnandy-tfstate"
}

import {
  to = aws_iam_role.lambda_role
  id = "vsnandy_lambda_role"
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
// Assign the above policy as the asummed role for the lambda
resource "aws_iam_role" "lambda_role" {
  name = "vsnandy_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_policy.json
}

// IAM policy for logging from the lambda
data "aws_iam_policy_document" "lambda_logging_policy_document" {
  statement {
    effect = "Allow"
    resources = ["arn:aws:logs:*:*:*"]
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
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