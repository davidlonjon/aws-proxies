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

    Args:
        ec2 (object): EC2 resource
        vpcs (dict): Vpcs

    Returns:
        dict: vpcs
    """

    created_vpcs = []
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
                vpc['VpcId'] = vpc_id
            else:
                for found_vpc in found_vpcs:
                    vpc['VpcId'] = found_vpc.id
                logger.info('The VPC with CIDR block "%s" does already exists',
                            vpc['CidrBlock'],
                            )
            created_vpcs.append(vpc)
        except Exception as e:
            logger.error('The VPC with CIDR block "%s" could not be created. Error message %s',
                         vpc['CidrBlock'],
                         e.message)

    return created_vpcs


def create_internet_gateways(ec2, vpcs):
    """Create internet gateways

    Args:
        ec2 (object): EC2 resource
        vpcs (dict): Vpcs

    Returns:
        dict: internet gateways
    """
    created_igs = []
    for vpc in vpcs:
        if 'create_internet_gateway' in vpc:
            filters = [
                {
                    'Name': 'attachment.vpc-id',
                    'Values': [
                        vpc['VpcId'],
                    ]
                }
            ]

            found_igs = list(ec2.internet_gateways.filter(Filters=filters))
            if not found_igs:
                ig = ec2.create_internet_gateway()
                ec2.Vpc(vpc['VpcId']).attach_internet_gateway(
                    InternetGatewayId=ig.id,
                )
                ig_id = ig.id
            else:
                for found_ig in found_igs:
                    ig_id = found_ig.id
                logger.info('The internet gateway was already created')

            created_igs.append(
                {
                    'InternetGatewayId': ig_id,
                    'attachment.vpc-id': vpc['VpcId']
                }
            )

    return created_igs