# -*- coding: utf-8 -*-
import boto3
import logging
import sys


class AWSEC2Interface(object):

    def __init__(self, profile, **kwargs):
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
                'Could not create AWS EC2 resource. Error message %s', e.message)
            sys.exit()

        # Get AWS EC2 Client
        try:
            self.ec2_client = self.__get_client_from_resource(self.ec2)
            self.logger.info('AWS EC2 client created')
        except Exception as e:
            self.logger.error(
                'Could not create AWS EC2 client. Error message %s', e.message)
            sys.exit()

        self.eni_mappings = kwargs.pop('eni_mappings', None)
        self.cidr_suffix_ips_number_mapping = kwargs.pop(
            'cidr_suffix_ips_number_mapping', None)
        self.proxy_nodes_count = kwargs.pop('proxy_nodes_count', 1)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.config = {
            'vpcs': {},
            'instances': {}
        }

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

    def __get_client_from_resource(self, resource):
        """Get AWS resource

        Args:
            resource (object): AWS Resource

        Returns:
            object: EC2 resource
        """
        client = resource.meta.client
        return client

    # Taken from
    # http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
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

    def create_suffix(self, suffix, index):
        """Create suffix using an index

        Args:
            suffix (string): Base suffix
            index (int/string): Index

        Returns:
            string: Suffic
        """
        i = "%02d" % (int(index) + 1,)
        return suffix + '-' + i

    def create_name_tag_for_resource(self, resource, name_tag, suffix=''):
        """Create a name tag for a EC2 resource using a suffix if passed

        Args:
            resource (object): EC2 resource
            name_tag (dict): Tag dictionary
            suffix (str, optional): Suffic
        """
        if suffix:
            updated_name_tag = name_tag.copy()
            updated_name_tag['Value'] = name_tag['Value'] + '-' + suffix

        resource.create_tags(
            Tags=[updated_name_tag]
        )

    def create_vpcs(self, vpcs):
        """Create AWS VPCS if a VPC does not exist (checking cidr block)

        Args:
            ec2 (object): EC2 resource
            vpcs (dict): Vpcs

        Returns:
            dict: vpcs
        """

        created_vpcs = {}
        for index, vpc in enumerate(vpcs):
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

                    if 'BaseNameTag' in vpc:
                        suffix = self.create_suffix('vpc', index)
                        self.create_name_tag_for_resource(created_vpc, vpc['BaseNameTag'], suffix)

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
                    created_ig = self.ec2.create_internet_gateway()
                    self.ec2.Vpc(vpc['VpcId']).attach_internet_gateway(
                        InternetGatewayId=created_ig.id,
                    )

                    if 'BaseNameTag' in vpc:
                        suffix = self.create_suffix('ig', 0)
                        self.create_name_tag_for_resource(
                            created_ig, vpc['BaseNameTag'], suffix)

                    ig_id = created_ig.id
                    self.logger.info(
                        'The internet gateway with ID "%s" attached to VPC "%s" has been created',
                        created_ig.id,
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
                for index, subnet in enumerate(vpc['Subnets']):
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

                        if 'BaseNameTag' in vpc:
                            suffix = self.create_suffix('subnet', index)
                            self.create_name_tag_for_resource(
                                created_subnet, vpc['BaseNameTag'], suffix)

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
                for index, sg in enumerate(vpc['SecurityGroups']):
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

                        if 'BaseNameTag' in vpc:
                            suffix = self.create_suffix('sg', index)
                            self.create_name_tag_for_resource(
                                created_sg, vpc['BaseNameTag'], suffix)

                        sg_id = created_sg.id

                        if 'IngressRules' in sg:
                            self.authorize_sg_ingress_rules(created_sg, sg)

                        if 'EgressRules' in sg:
                            self.authorize_sg_egress_rules(created_sg, sg)

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

    def authorize_sg_ingress_rules(self, sg, sg_config):
        """Authorize security group ingress (inbound) rules

        Args:
            sg (object): Security group
            sg_config (dict): Security group config
        """
        for ingress_rule in sg_config['IngressRules']:
            if 'IpPermissions' in ingress_rule:
                sg.authorize_ingress(
                    IpPermissions=ingress_rule['IpPermissions'])

    def authorize_sg_egress_rules(self, sg, sg_config):
        """Authorize security group egress (outbound) rules

        Args:
            sg (object): Security group
            sg_config (dict): Security group config
        """
        for ingress_rule in sg_config['EgressRules']:
            if 'IpPermissions' in ingress_rule:
                sg.authorize_egress(IpPermissions=ingress_rule['IpPermissions'])
