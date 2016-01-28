# -*- coding: utf-8 -*-
import boto3
import logging
import sys


class AWSEC2Interface(object):

    def __init__(self, profile):
        """Constructor

        Args:
            profile (string): AWS profile
        """
        # Setup logger
        self.logger = self.__setup_logger()

        # Get AWS Session
        try:
            self.session = self.__get_session(profile)
            self.logger.info('AWS Session created')
        except Exception:
            self.logger.error('Could not open AWS session')
            sys.exit()

        # Get AWS EC2 Resource
        try:
            self.ec2 = self.__get_resource('ec2')
            self.logger.info('AWS EC2 resource created')
        except Exception as e:
            self.logger.error(
                'Could not access AWS EC2 resource. Error message %s', e.message)
            sys.exit()

    def __setup_logger(self):
        """Setup logger

        Returns:
            object: Logger
        """
        try:  # Python 2.7+
            from logging import NullHandler
        except ImportError:
            class NullHandler(logging.Handler):
                def emit(self, record):
                    pass

        logging.getLogger(__name__).addHandler(NullHandler())
        logging.basicConfig(level=logging.INFO)

        # Raise other modules log levels to make the logs for this module less cluttered with noise
        for _ in ("boto3", "botocore"):
            logging.getLogger(_).setLevel(logging.WARNING)

        return logging.getLogger(__name__)

    def __get_session(self, profile):
        """Get AWS Session

        Args:
            profile (string): AWS credential profile

        Returns:
            object: AWS session object
        """
        session = boto3.Session(profile_name=profile)
        return session

    def __get_resource(self, resource):
        """Get AWS resource

        Args:
            resource (string): AWS resource

        Returns:
            object: EC2 resource
        """
        resource = self.session.resource(resource)
        return resource

    def create_vpc(self, cidr_block, tags):
        """Create a single AWS VPC

        Args:
            cidr_block (string): Cidr block
            tags (dict): Tags

        Returns:
            string: VPC id
        """
        vpc = self.ec2.create_vpc(
            CidrBlock=cidr_block,
        )

        vpc.create_tags(
            Tags=tags
        )

        return vpc.vpc_id

    def create_vpcs(self, vpcs):
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

                found_vpcs = list(self.ec2.vpcs.filter(Filters=filters))

                if not found_vpcs:
                    vpc_id = self.create_vpc(
                        vpc['CidrBlock'], vpc['Tags'])
                    self.logger.info('A new VPC with CIDR block "%s" with ID %s has been created',
                                     vpc['CidrBlock'],
                                     vpc_id
                                     )
                    vpc['VpcId'] = vpc_id
                else:
                    for found_vpc in found_vpcs:
                        vpc['VpcId'] = found_vpc.id
                    self.logger.info('The VPC with CIDR block "%s" does already exists',
                                     vpc['CidrBlock'],
                                     )
                created_vpcs.append(vpc)
            except Exception as e:
                self.logger.error('The VPC with CIDR block "%s" could not be created. Error message %s',
                                  vpc['CidrBlock'],
                                  e.message)

        return created_vpcs

    def create_internet_gateways(self, vpcs):
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

                found_igs = list(
                    self.ec2.internet_gateways.filter(Filters=filters))
                if not found_igs:
                    ig = self.ec2.create_internet_gateway()
                    self.ec2.Vpc(vpc['VpcId']).attach_internet_gateway(
                        InternetGatewayId=ig.id,
                    )
                    ig_id = ig.id
                else:
                    for found_ig in found_igs:
                        ig_id = found_ig.id
                    self.logger.info(
                        'The internet gateway was already created')

                created_igs.append(
                    {
                        'InternetGatewayId': ig_id,
                        'attachment.vpc-id': vpc['VpcId']
                    }
                )

        return created_igs
