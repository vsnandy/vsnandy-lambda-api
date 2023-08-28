from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as _lambda,
    CfnResource,
    CfnOutput
)
from constructs import Construct

class VsnandyLambdaApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Defines an AWS Lambda resource
        my_lambda = _lambda.Function(
            self, 'Handler',
            runtime=_lambda.Runtime.PYTHON_3_10,
            code = _lambda.Code.from_asset('lambda'),
            handler = 'main.handler'
        )

        cfn_func_url = CfnResource(
            scope=self,
            id="lambdaFuncUrl",
            type="AWS::Lambda::Url",
            properties={
                "TargetFunctionArn": my_lambda.function_arn,
                "AuthType": "NONE",
                "Cors": {
                    "AllowOrigins": ["https://vsnandy.github.io"]
                }
            }
        )

        CfnResource(
            scope=self,
            id="funcURLPermission",
            type="AWS::Lambda::Permission",
            properties={
                "FunctionName": my_lambda.function_name,
                "Principal": "*",
                "Action": "lambda:InvokeFunctionUrl",
                "FunctionUrlAuthType": "NONE"
            }
        )

        CfnOutput(
            self, "FunctionURL",
            description="Lambda Function URL",
            value=cfn_func_url.get_att(attribute_name="FunctionUrl").to_string()
        )