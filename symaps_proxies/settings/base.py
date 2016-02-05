# -*- coding: utf-8 -*-

AWS_CONFIG_FILE = './config/aws_resources.json'
AWS_TAG_NAME_BASE = 'symaps-prod-proxies'
PROXY_NODES_COUNT = 4
AWS_INSTANCES_GROUPS_CONFIG = [
    {
        'InstanceType': 't1.micro',
        'ImageName': 'tinyproxy',
        'VPCCidrBlock': '15.0.0.0/16',
        'CidrBlockFormatting': '15.0.\{0\}.\{1\}',
        'SecurityGroups': [
            {
                'GroupName': 'default',
                'Description': 'Security group for proxies',
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8888,
                        'ToPort': 8888,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0'
                            },
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                            },
                        ]
                    }
                ]
            }
        ]
    }
]

# Instance Type, Maximum Elastic Network Interfaces, IP Addresses per Interface
AWS_ENI_MAPPINGS = [
    ('c1.medium', 2, 6),
    ('c1.xlarge', 4, 15),
    ('c3.large', 3, 10),
    ('c3.xlarge', 4, 15),
    ('c3.2xlarge', 4, 15),
    ('c3.4xlarge', 8, 30),
    ('c3.8xlarge', 8, 30),
    ('c4.large', 3, 10),
    ('c4.xlarge', 4, 15),
    ('c4.2xlarge', 4, 15),
    ('c4.4xlarge', 8, 30),
    ('c4.8xlarge', 8, 30),
    ('cc2.8xlarge', 8, 30),
    ('cg1.4xlarge', 8, 30),
    ('cr1.8xlarge', 8, 30),
    ('d2.xlarge', 4, 15),
    ('d2.2xlarge', 4, 15),
    ('d2.4xlarge', 8, 30),
    ('d2.8xlarge', 8, 30),
    ('g2.2xlarge', 4, 15),
    ('g2.8xlarge', 8, 30),
    ('hi1.4xlarge', 8, 30),
    ('hs1.8xlarge', 8, 30),
    ('i2.xlarge', 4, 15),
    ('i2.2xlarge', 4, 15),
    ('i2.4xlarge', 8, 30),
    ('i2.8xlarge', 8, 30),
    ('m1.small', 2, 4),
    ('m1.medium', 2, 6),
    ('m1.large', 3, 10),
    ('m1.xlarge', 4, 15),
    ('m2.xlarge', 4, 15),
    ('m2.2xlarge', 4, 30),
    ('m2.4xlarge', 8, 30),
    ('m3.medium', 2, 6),
    ('m3.large', 3, 10),
    ('m3.xlarge', 4, 15),
    ('m3.2xlarge', 4, 30),
    ('m4.large', 2, 10),
    ('m4.xlarge', 4, 5),
    ('m4.2xlarge', 4, 5),
    ('m4.4xlarge', 8, 0),
    ('m4.10xlarge', 8, 0),
    ('r3.large', 3, 0),
    ('r3.xlarge', 4, 5),
    ('r3.2xlarge', 4, 5),
    ('r3.4xlarge', 8, 0),
    ('r3.8xlarge', 8, 0),
    ('t1.micro', 2, 2),
    ('t2.nano', 2, 2),
    ('t2.micro', 2, 2),
    ('t2.small', 2, 4),
    ('t2.medium', 3, 6),
    ('t2.large', 3, 12),
]

AWS_HVM_ONLY_INSTANCE_TYPES = ['c4', 'd2',   'g2', 'i2', 'm4', 'r3', 't2']

# More info at http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html#SubnetSize
# AWS allow block size is between a /28 netmask and /16 netmask and reserve 5 ip addresses
CIDR_SUFFIX_IPS_NUMBER_MAPPING = [
    (11, '/28'),
    (27, '/27'),
    (59, '/26'),
    (123, '/25'),
    (251, '/24'),
    (507, '/23'),
    (1019, '/22'),
    (2043, '/21'),
    (4091, '/20'),
    (8187, '/19'),
    (16379, '/18'),
    (32763, '/17'),
    (64531, '/16'),
]
