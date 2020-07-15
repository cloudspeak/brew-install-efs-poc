import json

from typing import List, Dict
import pulumi
from pulumi.output import Input, Output
from pulumi.resource import ResourceOptions
from pulumi_aws import config, iam, kinesis, pinpoint, s3, ec2, efs, codebuild, ssm
from pulumi_aws.get_caller_identity import get_caller_identity

from .codebuild_policy import get_codebuild_base_policy, get_codebuild_vpc_policy
from .vpc import VPC

class EFS(pulumi.ComponentResource):
    """
    The `nuage:aws:DevelopmentEnvironment:EFS` component creates an EFS
    filesystem with targets in each public subnet and an access point
    at the root.
    """

    file_system_id: Output[efs.FileSystem]
    access_point: Output[efs.AccessPoint]

    
    def __init__(
        self,
        name,
        vpc_environment: VPC,
        opts=None,
    ):
        super().__init__("nuage:aws:DevelopmentEnvironment:EFS", f"{name}EfsEnvironment", None, opts)

        file_system = efs.FileSystem(f"{name}FileSystem")
        targets = []

        for i in range(0, len(vpc_environment.public_subnets)):
            targets.append(efs.MountTarget(f"{name}MountTarget{i}",
                file_system_id=file_system.id,
                subnet_id=vpc_environment.public_subnets[i].id,
                security_groups=[vpc_environment.security_group],
                opts=ResourceOptions(depends_on=[vpc_environment.security_group,vpc_environment.public_subnets[i]])
            ))

        access_point = efs.AccessPoint(f"{name}AccessPoint",
            file_system_id=file_system.id,
            posix_user={"uid": 1000, "gid": 1000},
            root_directory= { "path": "/", "creationInfo": { "ownerGid": 1000, "ownerUid": 1000, "permissions": "755" }  },
            opts=ResourceOptions(depends_on=targets)
        )

        outputs = {
            "file_system_id": file_system.id,
            "access_point": access_point
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

