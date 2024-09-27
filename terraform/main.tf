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