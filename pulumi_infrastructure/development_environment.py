import json

from typing import List, Dict
import pulumi
from pulumi.output import Input, Output
from pulumi.resource import ResourceOptions
from pulumi_aws import config, iam, kinesis, pinpoint, s3, ec2, efs, codebuild, ssm
from pulumi_aws.get_caller_identity import get_caller_identity

from .codebuild_policy import get_codebuild_base_policy, get_codebuild_vpc_policy
from .vpc import VPC
from .efs import EFS
from .codebuild import CodeBuild

class DevelopmentEnvironment(pulumi.ComponentResource):
    """
    The `nuage:aws:DevelopmentEnvironment` component creates a VPC, Elastic
    filesystem and CodeBuild project for developing Lambda functions which
    have dependencies stored on EFS.
    """

    security_group_id: Output[str]
    public_subnet_ids: Output[List[str]]
    private_subnet_id: Output[str]
    efs_access_point_arn: Output[str]
    file_system_id: Output[str]
    vpc_id: Output[str]
    pulumi_token_param_name: Output[str]

    
    def __init__(
        self,
        name,
        github_repo_name: Input[str],
        github_version_name: Input[str] = None,
        opts=None,
    ):
        super().__init__("nuage:aws:DevelopmentEnvironment", name, None, opts)

        vpc_environment = VPC(name)
        efs_environment = EFS(name, vpc_environment)
        codebuild_environment = CodeBuild(name,
                vpc_environment=vpc_environment,
                efs_environment=efs_environment,
                github_repo_name=github_repo_name,
                github_version_name=github_version_name
        )

        outputs = {
            "security_group_id": vpc_environment.security_group.id,
            "public_subnet_ids": [subnet.id for subnet in vpc_environment.public_subnets],
            "private_subnet_id": vpc_environment.private_subnet.id,
            "efs_access_point_arn": efs_environment.access_point.arn,
            "pulumi_token_param_name": codebuild_environment.pulumi_token_param_name,
            "file_system_id": efs_environment.file_system_id,
            "vpc_id": vpc_environment.vpc.id
        }

        self.set_outputs(outputs)

    def set_outputs(self, outputs: dict):
        """
        Adds the Pulumi outputs as attributes on the current object so they can be
        used as outputs by the caller, as well as registering them.
        """
        for output_name in outputs.keys():
            setattr(self, output_name, outputs[output_name])

        self.register_outputs(outputs)


