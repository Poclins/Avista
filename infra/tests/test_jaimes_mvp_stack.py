from __future__ import annotations

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from stacks.jaimes_mvp_stack import JaimesMvpStack


def _template() -> Template:
    app = cdk.App()
    stack = JaimesMvpStack(app, "JaimesMvpStack")
    return Template.from_stack(stack)


def test_creates_one_public_image_lambda_with_mvp_limits() -> None:
    template = _template()
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "Architectures": ["x86_64"],
            "MemorySize": 2048,
            "Timeout": 180,
            "EphemeralStorage": {"Size": 1024},
            "ReservedConcurrentExecutions": 5,
        },
    )
    template.resource_count_is("AWS::Lambda::Url", 1)
    template.has_resource_properties("AWS::Lambda::Url", {"AuthType": "NONE"})
    template.has_output("FunctionUrl", {})


def test_grants_only_required_bedrock_actions_on_all_resources() -> None:
    template = _template()
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        {
                            "Action": [
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                                "bedrock:InvokeModelWithBidirectionalStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                        }
                    ]
                )
            }
        },
    )


def test_has_short_log_retention_and_no_prohibited_services() -> None:
    template = _template()
    template.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7})
    prohibited = {
        "AWS::ApiGateway::RestApi",
        "AWS::ApiGatewayV2::Api",
        "AWS::EC2::VPC",
        "AWS::RDS::DBCluster",
        "AWS::RDS::DBInstance",
        "AWS::S3::Bucket",
        "AWS::CloudFront::Distribution",
        "AWS::ECS::Cluster",
        "AWS::ECS::Service",
        "AWS::SecretsManager::Secret",
    }
    resource_types = {
        resource["Type"]
        for resource in template.to_json()["Resources"].values()
    }
    assert resource_types.isdisjoint(prohibited)
