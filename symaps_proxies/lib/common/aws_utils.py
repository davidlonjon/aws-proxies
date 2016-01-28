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

        # Raise other modules log levels to make the logs for this module less
        # cluttered with noise
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

    # Taken from http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
    def merge_dicts(self, *dict_args):
        '''
        Given any number of dicts, shallow copy and merge into a new dict,
        precedence goes to key value pairs in latter dicts.
        '''
        result = {}
        for dictionary in dict_args:
            result.update(dictionary)
        return result

    def merge_config(self, conf1, conf2):
        new_conf = {}
        for key, value in conf2.iteritems():
            if key in conf1:
                new_conf[key] = self.merge_dicts(conf1[key], value)

        return new_conf

    def create_vpcs(self, vpcs):
        """Create AWS VPCS if a VPC does not exist (checking cidr block)

        Args:
            ec2 (object): EC2 resource
            vpcs (dict): Vpcs

        Returns:
            dict: vpcs
        """

        created_vpcs = {}
        for vpc in vpcs:
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
                    created_vpc = self.ec2.create_vpc(
                        CidrBlock=vpc['CidrBlock'],
                    )

                    if 'Tags' in vpc:
                        created_vpc.create_tags(
                            Tags=vpc['Tags']
                        )

                    self.logger.info('A new VPC with CIDR block "%s" with ID "%s" has been created',
                                     vpc['CidrBlock'],
                                     created_vpc.vpc_id
                                     )
                    vpc['VpcId'] = created_vpc.vpc_id
                else:
                    if len(found_vpcs) > 0:
                        vpc['VpcId'] = found_vpcs[0].id
                    self.logger.info('The VPC with CIDR block "%s" does already exists',
                                     vpc['CidrBlock'],
                                     )
                created_vpcs[vpc['VpcId']] = vpc

        return created_vpcs

    def delete_vpcs(self, vpcs):
        """Delete VPCs

        Args:
            vpcs (dict): VPCs
        """
        for vpc_id, vpc in vpcs.iteritems():
            filters = [
                {
                    'Name': 'cidrBlock',
                    'Values': [
                        vpc['CidrBlock'],
                    ]
                }
            ]

            found_vpcs = list(self.ec2.vpcs.filter(Filters=filters))

            if found_vpcs:
                for found_vpc in found_vpcs:
                    self.ec2.Vpc(found_vpc.id).delete()
                    self.logger.error('The VPC with id % s has been deleted',
                                      found_vpc.id
                                      )
            else:
                self.logger.error('No VPC(s) were deleted')

    def create_internet_gateways(self, vpcs):
        """Create internet gateways

        Args:
            ec2 (object): EC2 resource
            vpcs (dict): Vpcs

        Returns:
            dict: internet gateways
        """
        created_igs = []
        for vpc_id, vpc in vpcs.iteritems():
            if 'CreateInternetGateway' in vpc:
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
                    self.logger.info(
                        'The internet gateway with ID "%s" attached to VPC "%s" has been created',
                        ig.id,
                        vpc['VpcId']
                    )
                else:
                    for found_ig in found_igs:
                        ig_id = found_ig.id
                    self.logger.info(
                        'The internet gateway was already created')

                created_igs.append(
                    {
                        'InternetGatewayId': ig_id,
                    }
                )

        return {
            vpc['VpcId']: {
                'InternetGateways': created_igs
            }
        }

    def create_subnets(self, vpcs):
        created_subnets = []
        for vpc_id, vpc in vpcs.iteritems():
            if 'Subnets' in vpc:
                for subnet in vpc['Subnets']:
                    filters = [
                        {
                            'Name': 'cidrBlock',
                            'Values': [
                                subnet['CidrBlock'],
                            ]
                        }
                    ]

                    found_subnets = list(
                        self.ec2.subnets.filter(Filters=filters))

                    if not found_subnets:
                        created_subnet = self.ec2.create_subnet(
                            VpcId=vpc['VpcId'], CidrBlock=subnet['CidrBlock'])
                        created_subnet.create_tags(Tags=vpc['Tags'])

                        subnet_id = created_subnet.id
                        self.logger.info(
                            'A new subnet with CIDR block "%s" ' +
                            'with ID "%s" and attached to VPC "%s" has been created',
                            subnet['CidrBlock'],
                            subnet_id,
                            vpc['VpcId']
                        )
                    else:
                        for found_subnet in found_subnets:
                            subnet_id = found_subnet.id
                        self.logger.info('The subnet with CIDR block "%s" does already exists',
                                         subnet['CidrBlock'],
                                         )

                    created_subnets.append(
                        {
                            'SubnetId': subnet_id,
                            'CidrBlock': subnet['CidrBlock']
                        }
                    )

        return {
            vpc['VpcId']: {
                'Subnets': created_subnets
            }
        }

        return created_subnets

    def create_security_groups(self, vpcs):
        created_sgs = []
        for vpc_id, vpc in vpcs.iteritems():
            if 'SecurityGroups' in vpc:
                for sg in vpc['SecurityGroups']:
                    filters = [
                        {
                            'Name': 'group-name',
                            'Values': [
                                sg['GroupName'],
                            ]
                        }
                    ]

                    found_sgs = list(
                        self.ec2.security_groups.filter(Filters=filters))

                    if not found_sgs:
                        created_sg = self.ec2.create_security_group(
                            VpcId=vpc['VpcId'],
                            GroupName=sg['GroupName'],
                            Description=sg['Description'])

                        created_sg.create_tags(Tags=vpc['Tags'])

                        sg_id = created_sg.id
                        self.logger.info(
                            'A new security group with group name "%s" ' +
                            'with ID "%s" and attached to VPC "%s" has been created',
                            sg['GroupName'],
                            sg_id,
                            vpc['VpcId']
                        )
                    else:
                        for found_sg in found_sgs:
                            sg_id = found_sg.id
                        self.logger.info('The SecurityGroup with group name "%s" does already exists',
                                         sg['GroupName'],
                                         )

                    created_sgs.append(
                        {
                            'SecurityGroupId': sg_id,
                            'GroupName': sg['GroupName'],
                            'Description': sg['Description'],
                        }
                    )

        return {
            vpc['VpcId']: {
                'SecurityGroups': created_sgs
            }
        }

        return created_sgs
