# -*- coding: utf-8 -*-
PROXY_NODES_COUNT = 1
AWS_INSTANCES_GROUPS_CONFIG = [
    {
        'InstanceType': 't1.micro',
        'ImageName': 'tinyproxy',
        'VPCCidrBlock': 'x.x.x.x/x`',
        'CidrBlockFormatting': 'x.x.\{x\}.\{x\}',
        'SecurityGroups': [
            {
                'GroupName': 'default',
                'Description': 'Security group for proxies',
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 'XXXX',
                        'ToPort': 'XXXX',
                        'IpRanges': [
                            {
                                'CidrIp': 'x.x.x.x/x'
                            },
                        ]
                    },
                ]
            }
        ]
    }
]
