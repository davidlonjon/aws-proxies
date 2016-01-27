# -*- coding: utf-8 -*-

AWS_VPCS = [
    {
        'CidrBlock': '15.0.0.0/16',
        'Tags': [
            {
                'Key': 'Name',
                'Value': 'symaps-prod-proxies'
            }
        ]
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