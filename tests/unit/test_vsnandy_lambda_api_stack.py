import aws_cdk as core
import aws_cdk.assertions as assertions

from vsnandy_lambda_api.vsnandy_lambda_api_stack import VsnandyLambdaApiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in vsnandy_lambda_api/vsnandy_lambda_api_stack.py
def test_oidc_provider_created():
    app = core.App()
    stack = VsnandyLambdaApiStack(app, "vsnandy-lambda-api")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("Custom::AWSCDKOpenIdConnectProvider", {
        "Url": "https://token.actions.githubusercontent.com"
    })

def test_oidc_role_created():
    app = core.App()
    stack = VsnandyLambdaApiStack(app, "account-setup")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                }
            }]
        }
    })
