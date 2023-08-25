from aws_cdk import (
    CfnOutput,
    Stack,
    aws_iam as iam
)
from constructs import Construct

class VsnandyLambdaApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        github_provider = iam.OpenIdConnectProvider(self, "GithubProvider",
            url="https://token.actions.githubusercontent.com"                                            ,
            client_ids=["sts.amazonaws.com"]
        )

        CfnOutput(self, "GithubProviderArn", value=github_provider.open_id_connect_provider_arn)