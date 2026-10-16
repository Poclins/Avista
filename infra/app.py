"""CDK entrypoint for the independent jAImes MVP stack."""

from __future__ import annotations

import os

import aws_cdk as cdk

from stacks.jaimes_mvp_stack import JaimesMvpStack


app = cdk.App()
JaimesMvpStack(
    app,
    "JaimesMvpStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
    description="jAImes MVP: una Lambda de imagen con PWA, API e IA Bedrock.",
)
app.synth()
