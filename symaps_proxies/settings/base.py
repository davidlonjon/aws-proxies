# -*- coding: utf-8 -*-

AWS_CONFIG_FILE = './config/aws_resources.json'
AWS_VPCS = [
    {
        'CidrBlock': '15.0.0.0/16',
        'BaseNameTag': {
            'Key': 'Name',
            'Value': 'symaps-prod-proxies'
        },
        'CreateInternetGateway': True,
        'Subnets': [
            {
                'CidrBlock': '15.0.0.0/24',
            },
            {
                'CidrBlock': '15.0.1.0/24',
            }
        ],
        'SecurityGroups': [
            {
                'GroupName': 'proxies-sg',
                'Description': 'Security group for proxies',
                'IngressRules': [
                    {
                        'IpPermissions': [
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 8000,
                                'ToPort': 8000,
                                'IpRanges': [
                                    {
                                        'CidrIp': '0.0.0.0/0'
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        'IpPermissions': [
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 22,
                                'ToPort': 22,
                                'IpRanges': [
                                    {
                                        'CidrIp': '0.0.0.0/0'
                                    },
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
]