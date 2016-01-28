# -*- coding: utf-8 -*-

AWS_VPCS = [
    {
        'CidrBlock': '15.0.0.0/16',
        'Tags': [
            {
                'Key': 'Name',
                'Value': 'symaps-prod-proxies'
            }
        ],
        'CreateInternetGateway': True,
        'Subnets': [
            {
                'CidrBlock': '15.0.0.0/24',
            },
            {
                'CidrBlock': '15.0.1.0/24',
            }
        ]
    }
]
