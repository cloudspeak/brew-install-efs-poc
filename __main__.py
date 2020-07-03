"""Creates a Lambda and an EFS in a VPC"""

import pulumi
from pulumi import ResourceOptions
from pulumi_aws import lambda_, iam, ec2, efs

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
    cidr_block="172.32.1.0/24",   
)
subnet_2 = ec2.Subnet("exampleVpcSubnetB",
    availability_zone="eu-west-1b",
    vpc_id=vpc.id,
    cidr_block="172.32.2.0/24"
)
subnet_3 = ec2.Subnet("exampleVpcSubnetC",
    availability_zone="eu-west-1c",
    vpc_id=vpc.id,
    cidr_block="172.32.3.0/24"
)

security_group = ec2.SecurityGroup("exampleSecurityGroup", vpc_id=vpc.id)

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
  vpc_id=vpc.id
)

gateway_route = ec2.Route("exampleGatewayRoute",
  destination_cidr_block="0.0.0.0/0",
  gateway_id=gateway.id,
  route_table_id=vpc.default_route_table_id
)


# EFS

file_system = efs.FileSystem("exampleFileSystem")
targets = []

for i in range(0, len(subnets)):
  targets.append(efs.MountTarget(f"exampleMountTarget{i}",
      file_system_id=file_system.id,
      subnet_id=subnets[i].id,
      security_groups=[security_group]
  ))

access_point = efs.AccessPoint("exampleAccessPoint",
    file_system_id=file_system.id,
    posix_user={"uid": 1000, "gid": 1000},
    root_directory= { "path": "/", "creationInfo": { "ownerGid": 1000, "ownerUid": 1000, "permissions": "755" }  },
    opts=ResourceOptions(depends_on=targets)
)


# Lambda

mount_location = "/mnt/efs"

example_function = lambda_.Function("exampleFunction",
        code="lambda.zip",
        name="my_lambda",
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
        }
)

pulumi.export('file_system_id', file_system.id)
pulumi.export('vpc_id', vpc.id)
pulumi.export('vpc_subnets', [subnet_1.id, subnet_2.id, subnet_3.id])
pulumi.export('security_group_id', security_group.id)


