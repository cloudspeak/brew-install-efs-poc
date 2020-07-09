"""Creates a Lambda and an EFS in a VPC"""

import json
import pulumi
from pulumi import ResourceOptions
from pulumi_aws import lambda_, iam, ec2, efs, codebuild, ssm
from pulumi_aws.get_caller_identity import get_caller_identity
from pulumi.output import Output
from typing import Dict
from filebase64sha256 import filebase64sha256

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


# VPC

vpc = ec2.Vpc("exampleVpc",
    cidr_block="172.32.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True
)
subnet_1 = ec2.Subnet("exampleVpcSubnetA",
    availability_zone="eu-west-1a",
    vpc_id=vpc.id,
    cidr_block="172.32.0.0/20",
    opts=ResourceOptions(depends_on=[vpc])
)
subnet_2 = ec2.Subnet("exampleVpcSubnetB",
    availability_zone="eu-west-1b",
    vpc_id=vpc.id,
    cidr_block="172.32.16.0/20",
    opts=ResourceOptions(depends_on=[vpc])
)
subnet_3 = ec2.Subnet("exampleVpcSubnetC",
    availability_zone="eu-west-1c",
    vpc_id=vpc.id,
    cidr_block="172.32.32.0/20",
    opts=ResourceOptions(depends_on=[vpc])
)

private_subnet_1 = ec2.Subnet("exampleVpcPrivateSubnetA",
    availability_zone="eu-west-1a",
    vpc_id=vpc.id,
    cidr_block="172.32.48.0/20",
    opts=ResourceOptions(depends_on=[vpc])
)


security_group = ec2.SecurityGroup("exampleSecurityGroup",
    vpc_id=vpc.id,
    opts=ResourceOptions(depends_on=[vpc])
)

security_group_rule = ec2.SecurityGroupRule("exampleSSHRule",
    security_group_id=security_group.id,
    type="ingress",
    protocol="tcp",
    from_port=22,
    to_port=22,
    cidr_blocks=["0.0.0.0/0"]
)

security_group_rule = ec2.SecurityGroupRule("exampleInboundRule",
    security_group_id=security_group.id,
    type="ingress",
    protocol="all",
    from_port=0,
    to_port=65535,
    source_security_group_id=security_group.id
)
security_group_rule = ec2.SecurityGroupRule("exampleOutboundRule",
    security_group_id=security_group.id,
    type="egress",
    protocol="all",
    from_port=0,
    to_port=65535,
    cidr_blocks=["0.0.0.0/0"],

)

subnets = [subnet_1, subnet_2, subnet_3]

gateway = ec2.InternetGateway("exampleInternetGateway",
    vpc_id=vpc.id,
    opts=ResourceOptions(depends_on=[vpc])
)

gateway_route = ec2.Route("exampleGatewayRoute",
  destination_cidr_block="0.0.0.0/0",
  gateway_id=gateway.id,
  route_table_id=vpc.default_route_table_id
)

elastic_ip = ec2.Eip("exampleEip",
    vpc=True,
    opts=ResourceOptions(depends_on=[gateway])
)

nat_gateway = ec2.NatGateway("exampleNatGateway",
    subnet_id=subnet_1.id,
    allocation_id=elastic_ip.id,
    opts=ResourceOptions(depends_on=[subnet_1,elastic_ip])
)

private_route_table = ec2.RouteTable("examplePrivateRouteTable",
    routes=[
      {
          "cidr_block": "0.0.0.0/0",
          "nat_gateway_id": nat_gateway.id,
      },
    ],
    vpc_id=vpc.id,
    opts=ResourceOptions(depends_on=[private_subnet_1])
)

private_route_table_assoc = ec2.RouteTableAssociation("examplePrivateRouteTableAssoc",
    route_table_id=private_route_table.id,
    subnet_id=private_subnet_1.id
)



# EFS

file_system = efs.FileSystem("exampleFileSystem")
targets = []

for i in range(0, len(subnets)):
  targets.append(efs.MountTarget(f"exampleMountTarget{i}",
      file_system_id=file_system.id,
      subnet_id=subnets[i].id,
      security_groups=[security_group],
      opts=ResourceOptions(depends_on=[security_group,subnets[i]])
  ))

access_point = efs.AccessPoint("exampleAccessPoint",
    file_system_id=file_system.id,
    posix_user={"uid": 1000, "gid": 1000},
    root_directory= { "path": "/", "creationInfo": { "ownerGid": 1000, "ownerUid": 1000, "permissions": "755" }  },
    opts=ResourceOptions(depends_on=targets)
)

# CodeBuild

github_repo = "https://github.com/cloudspeak/brew-install-efs-poc.git"
github_version = "codebuild"

def get_codebuild_vpc_policy(account_id: str, subnet_id: Output[str]) -> Output[Dict]:
  return subnet_id.apply(lambda subnet_id_value: {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeDhcpOptions",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcs"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterfacePermission"
            ],
            "Resource": f"arn:aws:ec2:eu-west-1:{account_id}:network-interface/*",
            "Condition": {
                "StringEquals": {
                    "ec2:Subnet": [
                        f"arn:aws:ec2:eu-west-1:{account_id}:subnet/{subnet_id_value}"
                    ],
                    "ec2:AuthorizedService": "codebuild.amazonaws.com"
                }
            }
        }
    ]
})

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

def get_codebuild_base_policy(account_id: str, project_name: str) -> Dict:
  return {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Resource": [
                f"arn:aws:logs:eu-west-1:{account_id}:log-group:/aws/codebuild/{project_name}",
                f"arn:aws:logs:eu-west-1:{account_id}:log-group:/aws/codebuild/{project_name}:*"
            ],
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ]
        },
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::codepipeline-eu-west-1-*"
            ],
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:GetBucketAcl",
                "s3:GetBucketLocation"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "codebuild:CreateReportGroup",
                "codebuild:CreateReport",
                "codebuild:UpdateReport",
                "codebuild:BatchPutTestCases"
            ],
            "Resource": [
                f"arn:aws:codebuild:eu-west-1:{account_id}:report-group/{project_name}-*"
            ]
        }
    ]
}

account_id = get_caller_identity().account_id

#TODO randomize

project_name = "ExampleBuildDeploy"

pulumi_token_param = ssm.Parameter("examplePulumiAccessToken",
    type="SecureString",
    value="none"
)

codebuild_vpc_policy = iam.Policy("exampleCodeBuildVpcPolicy",
    policy=get_codebuild_vpc_policy(account_id, private_subnet_1.id).apply(json.dumps)
)

codebuild_base_policy = iam.Policy("exampleCodeBuildBasePolicy",
    policy=json.dumps(get_codebuild_base_policy(account_id, project_name))
)

codebuild_service_role_policy = iam.Policy("exampleCodeBuildServiceRolePolicy",
    policy=json.dumps(get_codebuild_serice_role_policy())
)

codebuild_service_role = iam.Role("exampleCodeBuildRole",
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

codebuild_vpn_policy_attach = iam.PolicyAttachment("exampleCodeBuildVpnAttachment",
  policy_arn=codebuild_vpc_policy.arn,
  roles=[codebuild_service_role.name]
)

codebuild_base_policy_attach = iam.PolicyAttachment("exampleCodeBuildBaseAttachment",
  policy_arn=codebuild_base_policy.arn,
  roles=[codebuild_service_role.name]
)

codebuild_service_role_policy_attach = iam.PolicyAttachment("exampleCodeBuildServiceRoleAttachment",
  policy_arn=codebuild_service_role_policy.arn,
  roles=[codebuild_service_role.name]
)

codebuild_project = codebuild.Project("exampleCodeBuildProject",
    description="Builds and deploys the stack",
    name=project_name,
    vpc_config={
      "vpc_id": vpc.id,
      "subnets": [private_subnet_1],
      "security_group_ids": [security_group.id]
    },
    source={
      "type": "GITHUB",
      "location": github_repo
    },
    source_version=github_version,
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
        }
      ]
    },
    service_role=codebuild_service_role.arn,
    opts=ResourceOptions(depends_on=[vpc,*subnets,security_group])
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
          "security_group_ids": [security_group.id],
          "subnet_ids": [subnet_1.id, subnet_2.id, subnet_3.id]
        },
        file_system_config={
          "arn": access_point.arn,
          "local_mount_path": mount_location
        },
        environment={
          "variables": {
            "LAMBDA_PACKAGES_PATH": mount_location,
            "LD_LIBRARY_PATH": f"/var/lang/lib:/lib64:/usr/lib64:/var/runtime:/var/runtime/lib:/var/task:/var/task/lib:/opt/lib:{mount_location}/lambda_packages/lib",
            "PATH": f"/var/lang/bin:/usr/local/bin:/usr/bin/:/bin:/opt/bin:{mount_location}/lambda_packages/bin"
          }
        },
        opts=ResourceOptions(depends_on=[*subnets,security_group,access_point,example_role])
)

pulumi.export('file_system_id', file_system.id)
pulumi.export('vpc_id', vpc.id)
pulumi.export('public_subnets', [subnet_1.id, subnet_2.id, subnet_3.id])
pulumi.export('private_subnet', private_subnet_1.id)
pulumi.export('security_group_id', security_group.id)
pulumi.export('pulumi_access_token_parameter', pulumi_token_param.name)
