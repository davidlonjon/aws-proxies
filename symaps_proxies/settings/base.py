# -*- coding: utf-8 -*-

AWS_VPCS = [
    {
        'cidr_block': '15.0.0.0/16',
        'tags': [
            {
                'Key': 'Name',
                'Value': 'symaps-prod-proxies'
            }
        ]
    },
    {
        'cidr_block': '16.0.0.0/16',
        'tags': [
            {
                'Key': 'Name',
                'Value': 'symaps-prod-proxies'
            }
        ]
    }
]