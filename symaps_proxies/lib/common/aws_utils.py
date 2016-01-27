# -*- coding: utf-8 -*-
import boto3
import logging

logger = logging.getLogger(__name__)


def get_session(profile):
    """Get AWS Session

    Args:
        profile (string): AWS credential profile

    Returns:
        object: AWS session object
    """
    session = boto3.Session(profile_name=profile)
    return session


def get_resource(session, resource):
    """Get AWS resource

    Args:
        session (object): AWS session
        resource (string): AWS resource

    Returns:
        object: EC2 resource
    """
    resource = session.resource(resource)
    return resource


def create_vpc(ec2, cidr_block, tags):
    """Create a single AWS VPC

    Args:
        ec2 (object): EC2 Resource
        cidr_block (string): Cidr block
        tags (dict): Tags

    Returns:
        string: VPC id
    """
    vpc = ec2.create_vpc(
        CidrBlock=cidr_block,
    )

    vpc.create_tags(
        Tags=tags
    )

    return vpc.vpc_id


def create_internet_gateways(ec2, vpcs):
    for vpc in vpcs:
        if 'create_internet_gateway' in vpc:



def create_vpcs(ec2, vpcs):
    """Create AWS VPCS if a VPC does not exist (checking cidr block)
    """
    for vpc in vpcs:
        try:
            filters = [
                {
                    'Name': 'cidrBlock',
                    'Values': [
                        vpc['CidrBlock'],
                    ]
                }
            ]

            found_vpcs = list(ec2.vpcs.filter(Filters=filters))

            if not found_vpcs:
                vpc_id = create_vpc(ec2, vpc['CidrBlock'], vpc['Tags'])
                logger.info('A new VPC with CIDR block "%s" with ID %s has been created',
                            vpc['CidrBlock'],
                            vpc_id
                            )
            else:
                logger.info('The VPC with CIDR block "%s" does already exists',
                            vpc['CidrBlock'],
                            )
        except Exception as e:
            logger.error('The VPC with CIDR block "%s" could not be created. Error message %s',
                         vpc['CidrBlock'],
                         e.message)
