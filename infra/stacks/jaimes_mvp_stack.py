"""Independent, minimal infrastructure for the jAImes cloud demo."""

from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class JaimesMvpStack(cdk.Stack):
    """One public image Lambda serving FastAPI and the React PWA."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repository_root = str(Path(__file__).resolve().parents[2])
        function = lambda_.DockerImageFunction(
            self,
            "Function",
            code=lambda_.DockerImageCode.from_image_asset(repository_root),
            architecture=lambda_.Architecture.X86_64,
            memory_size=2048,
            timeout=cdk.Duration.seconds(180),
            ephemeral_storage_size=cdk.Size.mebibytes(1024),
            reserved_concurrent_executions=5,
        )

        logs.LogGroup(
            self,
            "FunctionLogGroup",
            log_group_name=f"/aws/lambda/{function.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:InvokeModelWithBidirectionalStream",
                ],
                resources=["*"],
            )
        )

        function_url = function.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
        )
        public_invoke = lambda_.CfnPermission(
            self,
            "PublicInvokeViaFunctionUrl",
            action="lambda:InvokeFunction",
            function_name=function.function_name,
            principal="*",
            function_url_auth_type="NONE",
        )
        public_invoke.add_override("Properties.InvokedViaFunctionUrl", True)

        cdk.CfnOutput(
            self,
            "FunctionUrl",
            value=function_url.url,
            description="URL publica HTTPS de la demo jAImes.",
        )
