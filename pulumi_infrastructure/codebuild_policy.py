from typing import Dict
from pulumi.output import Output


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
