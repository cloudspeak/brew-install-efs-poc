import json

from typing import List, Dict
import pulumi
from pulumi.output import Input, Output
from pulumi.resource import ResourceOptions
from pulumi_aws import config, iam, kinesis, pinpoint, s3, ec2, efs, codebuild, ssm
from pulumi_aws.get_caller_identity import get_caller_identity


class VPC(pulumi.ComponentResource):
    """
    The `nuage:aws:DevelopmentEnvironment:VPC` component creates a VPC with
    three public subnets and one private subnet.  One of the public subnets
    contains a NAT gateway, allowing the private subnet to access the internet.
    """

    vpc: Output[ec2.Vpc]
    security_group: Output[ec2.SecurityGroup]
    public_subnets: Output[List[ec2.Subnet]]
    private_subnet: Output[ec2.Subnet]
    nat_gateway: Output[ec2.NatGateway]

    
    def __init__(
        self,
        name,
        opts=None,
    ):
        super().__init__("nuage:aws:DevelopmentEnvironment:VPC", f"{name}VpcEnvironment", None, opts)


        vpc = ec2.Vpc(f"{name}Vpc",
            cidr_block="172.32.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True
        )
        subnet_1 = ec2.Subnet(f"{name}VpcSubnetA",
            availability_zone="eu-west-1a",
            vpc_id=vpc.id,
            cidr_block="172.32.0.0/20",
            opts=ResourceOptions(depends_on=[vpc])
        )
        subnet_2 = ec2.Subnet(f"{name}VpcSubnetB",
            availability_zone="eu-west-1b",
            vpc_id=vpc.id,
            cidr_block="172.32.16.0/20",
            opts=ResourceOptions(depends_on=[vpc])
        )
        subnet_3 = ec2.Subnet(f"{name}VpcSubnetC",
            availability_zone="eu-west-1c",
            vpc_id=vpc.id,
            cidr_block="172.32.32.0/20",
            opts=ResourceOptions(depends_on=[vpc])
        )

        private_subnet_1 = ec2.Subnet(f"{name}VpcPrivateSubnetA",
            availability_zone="eu-west-1a",
            vpc_id=vpc.id,
            cidr_block="172.32.48.0/20",
            opts=ResourceOptions(depends_on=[vpc])
        )


        security_group = ec2.SecurityGroup(f"{name}SecurityGroup",
            vpc_id=vpc.id,
            opts=ResourceOptions(depends_on=[vpc])
        )

        security_group_rule = ec2.SecurityGroupRule(f"{name}SSHRule",
            security_group_id=security_group.id,
            type="ingress",
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"]
        )

        security_group_rule = ec2.SecurityGroupRule(f"{name}InboundRule",
            security_group_id=security_group.id,
            type="ingress",
            protocol="all",
            from_port=0,
            to_port=65535,
            source_security_group_id=security_group.id
        )
        security_group_rule = ec2.SecurityGroupRule(f"{name}OutboundRule",
            security_group_id=security_group.id,
            type="egress",
            protocol="all",
            from_port=0,
            to_port=65535,
            cidr_blocks=["0.0.0.0/0"],

        )

        subnets = [subnet_1, subnet_2, subnet_3]

        gateway = ec2.InternetGateway(f"{name}InternetGateway",
            vpc_id=vpc.id,
            opts=ResourceOptions(depends_on=[vpc])
        )

        gateway_route = ec2.Route(f"{name}GatewayRoute",
        destination_cidr_block="0.0.0.0/0",
        gateway_id=gateway.id,
        route_table_id=vpc.default_route_table_id
        )

        elastic_ip = ec2.Eip(f"{name}Eip",
            vpc=True,
            opts=ResourceOptions(depends_on=[gateway])
        )

        nat_gateway = ec2.NatGateway(f"{name}NatGateway",
            subnet_id=subnet_1.id,
            allocation_id=elastic_ip.id,
            opts=ResourceOptions(depends_on=[subnet_1,elastic_ip])
        )

        private_route_table = ec2.RouteTable(f"{name}PrivateRouteTable",
            routes=[
              {
                  "cidr_block": "0.0.0.0/0",
                  "nat_gateway_id": nat_gateway.id,
              },
            ],
            vpc_id=vpc.id,
            opts=ResourceOptions(depends_on=[private_subnet_1])
        )

        private_route_table_assoc = ec2.RouteTableAssociation(f"{name}PrivateRouteTableAssoc",
            route_table_id=private_route_table.id,
            subnet_id=private_subnet_1.id
        )
        
        outputs = {
            "vpc": vpc,
            "security_group": security_group,
            "public_subnets": [subnet_1, subnet_2, subnet_3],
            "private_subnet": private_subnet_1,
            "nat_gateway": nat_gateway
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


