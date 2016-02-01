# -*- coding: utf-8 -*-
from __future__ import division
import boto3
import logging
import math
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
            'instance_types': []
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

    def bootstrap_vpcs_infrastructure(self, vpcs):
        """Bootstrap VPCS infrastructure

        Args:
            vpcs (object): VPCS base config

        """
        created_vpcs = self.create_vpcs(vpcs)
        self.config['vpcs'] = created_vpcs

        # Create Internet Gateways associated to VPCs
        internet_gateways = self.create_internet_gateways(self.config['vpcs'])
        self.config['vpcs'] = self.merge_config(self.config['vpcs'], internet_gateways)

        # Create subnets
        subnets = self.create_subnets(self.config['vpcs'])
        self.config['vpcs'] = self.merge_config(self.config['vpcs'], subnets)

        # Create Security groups
        security_groups = self.create_security_groups(self.config['vpcs'])
        self.config['vpcs'] = self.merge_config(self.config['vpcs'], security_groups)

        # Create route tables
        route_tables = self.create_route_tables(self.config['vpcs'])
        self.config['vpcs'] = self.merge_config(self.config['vpcs'], route_tables)

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
            found_vpcs = self.filter_resources(self.ec2.vpcs, 'cidrBlock', vpc['CidrBlock'])

            if not found_vpcs:
                created_vpc = self.ec2.create_vpc(
                    CidrBlock=vpc['CidrBlock'],
                )

                if 'BaseNameTag' in vpc:
                    suffix = self.create_suffix('vpc', index)
                    self.create_name_tag_for_resource(
                        created_vpc, vpc['BaseNameTag'], suffix)

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
            found_vpcs = self.filter_resources(self.ec2.vpcs, 'cidrBlock', vpc['CidrBlock'])

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
        index = 0
        for vpc_id, vpc in vpcs.iteritems():
            if 'CreateInternetGateway' in vpc:
                found_igs = self.filter_resources(self.ec2.internet_gateways, 'attachment.vpc-id', vpc['VpcId'])

                if not found_igs:
                    created_ig = self.ec2.create_internet_gateway()
                    self.ec2.Vpc(vpc['VpcId']).attach_internet_gateway(
                        InternetGatewayId=created_ig.id,
                    )

                    if 'BaseNameTag' in vpc:
                        suffix = self.create_suffix('ig', index)
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

                index = index + 1

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
                    found_subnets = self.filter_resources(self.ec2.subnets, 'cidrBlock', subnet['CidrBlock'])

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
        """Create security groups

        Args:
            vpcs (object): VPCS Config

        Returns:
            object: Security group config
        """
        created_sgs = []
        for vpc_id, vpc in vpcs.iteritems():
            if 'SecurityGroups' in vpc:
                for index, sg in enumerate(vpc['SecurityGroups']):
                    found_sgs = self.filter_resources(self.ec2.security_groups, 'group-name', sg['GroupName'])

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
                sg.authorize_egress(
                    IpPermissions=ingress_rule['IpPermissions'])

    def create_route_tables(self, vpcs):
        created_route_tables = []
        index = 0
        for vpc_id, vpc in vpcs.iteritems():
            found_route_tables = self.filter_resources(self.ec2.route_tables, 'vpc-id', vpc_id)

            if not found_route_tables:
                created_route_table = self.ec2.create_route_table(
                    VpcId=vpc_id
                )

                if 'BaseNameTag' in vpc:
                    suffix = self.create_suffix('rt', index)
                    self.create_name_tag_for_resource(
                        created_route_table, vpc['BaseNameTag'], suffix)

                route_table_id = created_route_table.id
                self.logger.info(
                    'A new route table ' +
                    'with ID "%s" and attached to VPC "%s" has been created',
                    route_table_id,
                    vpc_id
                )
            else:
                for found_route_tables in found_route_tables:
                    route_table_id = found_route_tables.id
                self.logger.info('The route table attached to VPC ID "%s" already exists',
                                 vpc_id,
                                 )

            created_route_tables.append(
                {
                    'RouteTableId': route_table_id,
                    'VpcId': vpc_id
                }
            )

            index = index + 1
        return {
            vpc['VpcId']: {
                'RouteTable': created_route_tables
            }
        }

    def get_image_id_from_name(self, image_name):
        """Get AMI image ID from AMI name

        Args:
            image_name (string): AMI image name

        Returns:
            string: AMI image ID
        """
        filters = [
            {
                'Name': 'name',
                'Values': [
                    image_name,
                ]
            }
        ]

        found_images = list(self.ec2.images.filter(Filters=filters))

        image_id = None
        if found_images and len(found_images) == 1:
            image_id = found_images[0].id

        return image_id

    def get_instance_eni_mapping(self, instance_type):
        """Get instance elastic network interface mapping

        Args:
            instance_type (string): Instance type

        Returns:
            Tuple: Instance elastic network interface mapping
        """
        instance_eni_mapping = []

        if self.eni_mappings is not None:
            instance_eni_mapping = [
                item for item in self.eni_mappings if item[0] == instance_type]
        return instance_eni_mapping

    def get_subnet_cidr_suffix(self, proxy_nodes_count):
        """Get subnet cidr suffix

        Args:
            proxy_nodes_count (integer): proxy nodes count

        Returns:
            string: subnet cidr suffix
        """
        cidr_suffix = "/28"
        if self.cidr_suffix_ips_number_mapping is not None:
            for item in self.cidr_suffix_ips_number_mapping:
                if item[0] > proxy_nodes_count:
                    cidr_suffix = item[1]
                    break

        return cidr_suffix

    def get_subnet_cidr_block(self, cidr_block_formatting, instance_index, subnet_suffix):
        """Get subnet cidr block

        Args:
            cidr_block_formatting (string): Cidr block formating
            instance_index (integer): Instance index
            subnet_suffix (string): subnet suffix

        Returns:
            string: Subnet cidr block
        """
        subnet_cidr_block = cidr_block_formatting.format(instance_index, 0) + subnet_suffix
        return subnet_cidr_block

    def bootstrap_instances_infrastucture(self, instance_types_config):
        created_instance_types_config = self.setup_instance_types_config(instance_types_config)

        self.config['instance_types'].append(created_instance_types_config)

    def setup_instance_types_config(self, instances_config):
        created_instance_type_config = []
        for instance_config in instances_config:
            if 'ImageName' in instance_config:
                image_id = self.get_image_id_from_name(
                    instance_config['ImageName'])
                instance_config['ImageId'] = image_id
            elif 'ImageId' in instance_config:
                image_id = instance_config['ImageId']

            instance_enis_count = 1
            instance_eni_private_ips_count = 1
            instance_eni_public_ips_count = 1
            instance_eni_mapping = self.get_instance_eni_mapping(
                instance_config['InstanceType'])
            if instance_eni_mapping:
                instance_enis_count = instance_eni_mapping[0][1]
                instance_eni_private_ips_count = instance_eni_mapping[0][2]
                instance_eni_public_ips_count = instance_eni_mapping[0][2]

            # print "instance_enis_count: {0}".format(instance_enis_count)
            # print "instance_eni_private_ips_count: {0}".format(instance_eni_private_ips_count)
            # print "instance_eni_public_ips_count: {0}".format(instance_eni_public_ips_count)

            instance_possible_ips_count = instance_eni_private_ips_count * \
                instance_enis_count

            # print "instance_possible_ips_count: {0}".format(instance_possible_ips_count)
            # print "self.proxy_nodes_count: {0}".format(self.proxy_nodes_count)
            # subnets_count = instance_enis_count
            # print "subnets_count: {0}".format(subnets_count)
            instance_per_type_count = int(
                math.ceil(self.proxy_nodes_count / instance_possible_ips_count))

            # print "instance_per_type_count: {0}".format(instance_per_type_count)
            instance_config['MinCount'] = instance_per_type_count
            instance_config['MaxCount'] = instance_per_type_count

            subnet_cidr_suffix = self.get_subnet_cidr_suffix(self.proxy_nodes_count)
            subnet_cidr_block = self.get_subnet_cidr_block(
                instance_config['CidrBlockFormatting'], 0, subnet_cidr_suffix)

            # print "*****"
            # print "subnet_cidr_suffix: {0}".format(subnet_cidr_suffix)

            instance_config['instances'] = []
            possible_ips_remaining = self.proxy_nodes_count
            for i in range(0, instance_per_type_count):
                instance_config['instances'].append({
                    'NetworkInterfaces': []
                })
                for j in range(0, instance_enis_count):
                    if possible_ips_remaining / instance_eni_private_ips_count > 1:
                        private_ips_count = instance_eni_private_ips_count
                    else:
                        private_ips_count = possible_ips_remaining

                    if possible_ips_remaining / instance_eni_public_ips_count > 1:
                        public_ips_count = instance_eni_public_ips_count
                    else:
                        public_ips_count = possible_ips_remaining

                    instance_config['instances'][i]['NetworkInterfaces'].append({
                        'Ips': [],
                        "Subnet": {
                            'CidrBlock': subnet_cidr_block
                        }

                    })

                    instance_config['instances'][i]['NetworkInterfaces'][j]['Ips'].append({
                        # Not counting the primary private ip address
                        'SecondaryPrivateIpAddressCount': private_ips_count - 1,
                        # Not counting the primary public ip address
                        'SecondaryPublicIpAddressCount': public_ips_count - 1,
                    })

                    possible_ips_remaining = possible_ips_remaining - instance_eni_private_ips_count
                    if possible_ips_remaining <= 0:
                        break
            created_instance_type_config.append(instance_config)

            return created_instance_type_config

    # Taken from:
    # http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
    def query_yes_no(self, question, default="yes"):
        """Ask a yes/no question via raw_input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

        The "answer" return value is True for "yes" or False for "no".
        """
        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            sys.stdout.write(question + prompt)
            choice = raw_input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' "
                                 "(or 'y' or 'n').\n")

    def filter_resources(self, function, filter_name, filter_value):
        values = [filter_value]
        if type(filter_value) is list:
            values = filter_value

        filters = [{
            'Name': filter_name,
            'Values': values
        }]

        return list(function.filter(Filters=filters))
