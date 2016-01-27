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
        'create_internet_gateway': True
    },
    {
        'CidrBlock': '16.0.0.0/16',
        'Tags': [
            {
                'Key': 'Name',
                'Value': 'symaps-prod-proxies'
            }
        ]
    }
]