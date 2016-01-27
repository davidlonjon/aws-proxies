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


def create_vpcs(ec2, vpcs):
    """Create AWS VPCS if a VPC does not exist (checking cidr block)
    """
    for vpc in vpcs:
        try:
            filters = [
                {
                    'Name': 'cidrBlock',
                    'Values': [
                        vpc['cidr_block'],
                    ]
                }
            ]

            found_vpcs = list(ec2.vpcs.filter(Filters=filters))

            if not found_vpcs:
                vpc_id = create_vpc(ec2, vpc['cidr_block'], vpc['tags'])
                logger.info('A new VPC with CIDR block "%s" with ID %s has been created',
                            vpc['cidr_block'],
                            vpc_id
                            )
            else:
                logger.info('The VPC with CIDR block "%s" does already exists',
                            vpc['cidr_block'],
                            )
        except Exception as e:
            logger.error('The VPC with CIDR block "%s" could not be created. Error message %s',
                         vpc['cidr_block'],
                         e.message)
