from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as _lambda
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
