"""Creates a Lambda and an EFS in a VPC"""

import json
import pulumi
from pulumi import ResourceOptions
from pulumi_aws import lambda_, iam, ec2, efs, codebuild, ssm
from pulumi_aws.get_caller_identity import get_caller_identity
from pulumi.output import Output
from typing import Dict
from filebase64sha256 import filebase64sha256
from pulumi_infrastructure.development_environment import DevelopmentEnvironment

environment = DevelopmentEnvironment("ExamplePOC",
  github_repo_name="https://github.com/cloudspeak/brew-install-efs-poc.git",
  github_version_name = "codebuild"
)

# IAM

example_role = iam.Role("ExampleFunctionRole", assume_role_policy="""{
"Version": "2012-10-17",
"Statement": [
    {
    "Action": "sts:AssumeRole",
    "Principal": {
        "Service": "lambda.amazonaws.com"
    },
    "Effect": "Allow",
    "Sid": ""
    }
]
}""")

iam.RolePolicyAttachment("VpcAccessPolicyAttach",
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
    role=example_role.name
)


# Lambda

mount_location = "/mnt/efs"

example_function = lambda_.Function("exampleFunction",
        code="lambda.zip",
        source_code_hash=filebase64sha256("lambda.zip"),
        handler="handler.my_handler",
        role=example_role.arn,
        runtime="python3.8",
        vpc_config={
          "security_group_ids": [environment.security_group_id],
          "subnet_ids": environment.public_subnet_ids
        },
        file_system_config={
          "arn": environment.efs_access_point_arn,
          "local_mount_path": mount_location
        },
        environment={
          "variables": {
            "LAMBDA_PACKAGES_PATH": mount_location,
            "LD_LIBRARY_PATH": f"/var/lang/lib:/lib64:/usr/lib64:/var/runtime:/var/runtime/lib:/var/task:/var/task/lib:/opt/lib:{mount_location}/lambda_packages/lib",
            "PATH": f"/var/lang/bin:/usr/local/bin:/usr/bin/:/bin:/opt/bin:{mount_location}/lambda_packages/bin"
          }
        },
        opts=ResourceOptions(depends_on=[environment])
)

pulumi.export('file_system_id', environment.file_system_id)
pulumi.export('vpc_id', environment.vpc_id)
pulumi.export('public_subnets', environment.public_subnet_ids)
pulumi.export('private_subnet', environment.private_subnet_id)
pulumi.export('security_group_id', environment.security_group_id)
pulumi.export('pulumi_access_token_parameter_name', environment.pulumi_token_param_name)
