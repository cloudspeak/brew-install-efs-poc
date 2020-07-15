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

class CodeBuild(pulumi.ComponentResource):
    """
    The `nuage:aws:DevelopmentEnvironment:CodeBuild` component creates a
    CodeBuild project which builds from a GitHub repository, from inside
    the VPC's private subnet so that it can access EFS.  It also
    creates a Systems Manager parameter for a Pulumi access token, which is
    passed to CodeBuild through an environment variable.
    """

    pulumi_token_param_name: Output[str]

    
    def __init__(
        self,
        name,
        vpc_environment: VPC,
        efs_environment: EFS,
        github_repo_name: Input[str],
        github_version_name: Input[str] = None,
        opts=None,
    ):
        super().__init__("nuage:aws:DevelopmentEnvironment:CodeBuild", f"{name}CodebuildEnvironment", None, opts)

        # TODO pass this in - with a default?
        def get_codebuild_serice_role_policy():
            return {
                "Version": "2012-10-17",
                "Statement": [
                    {
                    "Action": "*",
                    "Effect": "Allow",
                    "Resource": "*"
                    }
                ]
            }

        account_id = get_caller_identity().account_id

        #TODO add random chars on the end of default name to prevent conflicts
        project_name = f"{name}BuildDeploy"

        pulumi_token_param = ssm.Parameter(f"{name}PulumiAccessToken",
            type="SecureString",
            value="none"
        )

        codebuild_vpc_policy = iam.Policy(f"{name}CodeBuildVpcPolicy",
            policy=get_codebuild_vpc_policy(account_id, vpc_environment.private_subnet.id).apply(json.dumps)
        )

        codebuild_base_policy = iam.Policy(f"{name}CodeBuildBasePolicy",
            policy=json.dumps(get_codebuild_base_policy(account_id, project_name))
        )

        codebuild_service_role_policy = iam.Policy(f"{name}CodeBuildServiceRolePolicy",
            policy=json.dumps(get_codebuild_serice_role_policy())
        )

        codebuild_service_role = iam.Role(f"{name}CodeBuildRole",
            assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "codebuild.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }""")

        codebuild_vpn_policy_attach = iam.PolicyAttachment(f"{name}CodeBuildVpnAttachment",
            policy_arn=codebuild_vpc_policy.arn,
            roles=[codebuild_service_role.name]
        )

        codebuild_base_policy_attach = iam.PolicyAttachment(f"{name}CodeBuildBaseAttachment",
            policy_arn=codebuild_base_policy.arn,
            roles=[codebuild_service_role.name]
        )

        codebuild_service_role_policy_attach = iam.PolicyAttachment(f"{name}CodeBuildServiceRoleAttachment",
            policy_arn=codebuild_service_role_policy.arn,
            roles=[codebuild_service_role.name]
        )

        codebuild_project = codebuild.Project(f"{name}CodeBuildProject",
            description="Builds and deploys the stack",
            name=project_name,
            vpc_config={
                "vpc_id": vpc_environment.vpc.id,
                "subnets": [vpc_environment.private_subnet],
                "security_group_ids": [vpc_environment.security_group.id]
            },
            source={
                "type": "GITHUB",
                "location": github_repo_name
            },
            source_version=github_version_name,
            artifacts={
                "type": "NO_ARTIFACTS"
            },
            environment={
                "image": "aws/codebuild/amazonlinux2-x86_64-standard:2.0",
                "privileged_mode": True,
                "type": "LINUX_CONTAINER",
                "compute_type": "BUILD_GENERAL1_SMALL",
                "environment_variables": [
                    {
                        "name": "PULUMI_ACCESS_TOKEN",
                        "type": "PARAMETER_STORE",
                        "value": pulumi_token_param.name
                    },
                    {
                        "name": "FILESYSTEM_ID",
                        "type": "PLAINTEXT",
                        "value": efs_environment.file_system_id
                    }
                ]
            },
            service_role=codebuild_service_role.arn,
            opts=ResourceOptions(depends_on=[vpc_environment])
        )

        outputs = {
            "pulumi_token_param_name": pulumi_token_param.name
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

