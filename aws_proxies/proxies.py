# -*- coding: utf-8 -*-
from __future__ import division
import boto3
from instances import Instances
from internet_gateways import InternetGateways
import logging
from network_acls import NetworkAcls
from network_interfaces import NetworkInterfaces
import math
from route_tables import RouteTables
import settings
from security_groups import SecurityGroups
from subnets import Subnets
import sys
from utils import setup_logger, merge_config, get_subnet_cidr_block, \
    get_vpc_gateway_ip, get_subnet_cidr_suffix, get_instance_eni_mapping, \
    confirm_proxies_and_infra_creation, confirm_proxies_and_infra_deletion
from vpcs import Vpcs


class Proxies(object):

    def __init__(self, profile, **kwargs):
        """Constructor

        Args:
            profile (string): AWS profile
            **kwargs: Multiple arguments

        Raises:
            TypeError: Description
        """

        self.log_level = kwargs.pop("log_level", logging.WARNING)
        self.boto_log_level = kwargs.pop("boto_log_level", logging.WARNING)

        # Setup logger
        self.logger = setup_logger(__name__, self.log_level, self.boto_log_level)

        # Get AWS Session
        self.session = boto3.Session(profile_name=profile)
        self.logger.info("AWS Session created")

        # Get AWS EC2 Resource
        self.ec2 = self.session.resource("ec2")
        self.logger.info("AWS EC2 resource created")

        # Get AWS EC2 Client
        self.ec2_client = self.ec2.meta.client
        self.logger.info("AWS EC2 client created")

        self.eni_mapping = kwargs.pop("eni_mappings", settings.ENI_MAPPING)

        self.cidr_suffix_ips_number_mapping = kwargs.pop(
            "cidr_suffix_ips_number_mapping",
            settings.CIDR_SUFFIX_IPS_NUMBER_MAPPING
        )

        self.tag_base_name = kwargs.pop("tag_base_name", settings.TAG_BASE_NAME)

        self.hvm_only_instance_types = kwargs.pop(
            "hvm_only_instance_types",
            settings.HVM_ONLY_INSTANCE_TYPES
        )

        if kwargs:
            raise TypeError("Unexpected **kwargs: %r" % kwargs)

        self.config = {
            "vpcs": {},
            "instances_groups": []
        }

        resources_params = {
            "ec2": self.ec2,
            "ec2_client": self.ec2_client,
            "tag_base_name": self.tag_base_name,
            "log_level": self.log_level,
            "boto_log_level": self.boto_log_level
        }

        self.vpcs = Vpcs(**resources_params)
        self.internet_gateways = InternetGateways(**resources_params)
        self.subnets = Subnets(**resources_params)
        self.security_groups = SecurityGroups(**resources_params)
        self.route_tables = RouteTables(**resources_params)
        self.network_acls = NetworkAcls(**resources_params)
        self.network_interfaces = NetworkInterfaces(**resources_params)
        self.instances = Instances(**resources_params)

    def create(self, proxies_config, ask_confirm=True, silent=False):
        """Create proxies and its infrastructure

        Args:
            proxies_config (dict): Proxies config

        Raises:
            AttributeError
        """
        if "instances_config" not in proxies_config:
            raise AttributeError("The proxies config is missing the 'instances_config' attribute")

        if "available_ips" not in proxies_config:
            raise AttributeError("The proxies config is missing the 'available_ips' attribute")

        # Delete the proxies infrastructure first
        self.delete(ask_confirm=ask_confirm, silent=silent)

        # Setup proxies instances groups config
        created_instances_groups_config = self.__setup_instances_groups_config(proxies_config)

        self.config["instances_groups"].append(created_instances_groups_config)

        self.check_image_virtualization_against_instance_types(self.config["instances_groups"])

        if ask_confirm:
            if not confirm_proxies_and_infra_creation(self.config["instances_groups"], proxies_config['available_ips']):
                sys.exit()

        if not silent:
            print "\nCreating the vpc and starting the instances. Please wait..."

        # Create VPCS Infrastructure
        self.__bootstrap_vpcs_infrastructure(proxies_config['instances_config'])

        # Create network interfaces
        self.network_interfaces.create(self.config["vpcs"])

        # Associate ips to elastic network interfaces
        self.network_interfaces.associate_public_ips_to_enis()

        # Create instances
        self.instances.create(self.config['instances_groups'], self.config["vpcs"])

        if not silent:
            print "\nCreation completed. Instance(s) are booting up."

    def __bootstrap_vpcs_infrastructure(self, instances_config):
        """Bootstrap Vpcs infrastructure

        Args:
            instances_config (object): Instances config
        """
        base_vpcs_config = []

        base_vpcs_config.append(AWSProxies.__build_base_vpcs_config(instances_config))

        vpcs_config = self.vpcs.get_or_create(base_vpcs_config)

        self.config["vpcs"] = vpcs_config

        internet_gateways = self.internet_gateways.get_or_create(self.config["vpcs"])
        self.config["vpcs"] = merge_config(self.config["vpcs"], internet_gateways)

        subnets = self.subnets.get_or_create(self.config["vpcs"])
        self.config["vpcs"] = merge_config(self.config["vpcs"], subnets)

        security_groups = self.security_groups.get_or_create(self.config["vpcs"])
        self.config["vpcs"] = merge_config(self.config["vpcs"], security_groups)

        route_tables = self.route_tables.get_or_create(self.config["vpcs"])
        self.config["vpcs"] = merge_config(self.config["vpcs"], route_tables)

        self.route_tables.associate_subnets_to_routes(self.config["vpcs"])
        self.route_tables.create_ig_route(self.config["vpcs"])

        network_acls = self.network_acls.get_or_create(self.config["vpcs"])
        self.config["vpcs"] = merge_config(self.config["vpcs"], network_acls)

    def delete(self, ask_confirm=True, silent=False):
        """Delete proxies and its infrastructure
        """

        if ask_confirm:
            if not confirm_proxies_and_infra_deletion(self.tag_base_name):
                sys.exit()

        if not silent:
            print "\nDeleting the vpc and terminating the instances. Please wait..."

        self.network_interfaces.release_public_ips()
        self.instances.terminate()
        self.network_interfaces.delete()
        self.security_groups.delete()
        self.subnets.delete()
        self.route_tables.delete()
        self.network_acls.delete()
        self.internet_gateways.delete()
        self.vpcs.delete()

    def get_image_id_from_name(self, image_name):
        """Get AMI image ID from AMI name

        Args:
            image_name (string): AMI image name

        Returns:
            string: AMI image ID
        """
        filters = [
            {
                "Name": "name",
                "Values": [
                    image_name,
                ]
            }
        ]

        found_images = list(self.ec2.images.filter(Filters=filters))

        image_id = None
        if found_images and len(found_images) == 1:
            image_id = found_images[0].id

        return image_id

    def __setup_instances_groups_config(self, proxies_config):
        """Setup instance groups config

        Args:
            proxies_config (dict): Proxies config

        Returns:
            dict: Created instances config
        """
        created_instance_type_config = []

        for instance_config in proxies_config['instances_config']:
            if "ImageName" in instance_config:
                image_id = self.get_image_id_from_name(
                    instance_config["ImageName"])
                instance_config["ImageId"] = image_id
            elif "ImageId" in instance_config:
                image_id = instance_config["ImageId"]

            instance_enis_count = 1
            instance_eni_private_ips_count = 1
            instance_eni_public_ips_count = 1
            instance_eni_mapping = get_instance_eni_mapping(
                instance_type=instance_config["InstanceType"],
                eni_mapping=self.eni_mapping)
            if instance_eni_mapping:
                instance_enis_count = instance_eni_mapping[0][1]
                instance_eni_private_ips_count = instance_eni_mapping[0][2]
                instance_eni_public_ips_count = instance_eni_mapping[0][2]

            instance_possible_ips_count = instance_eni_private_ips_count * \
                instance_enis_count

            instance_per_type_count = int(
                math.ceil(proxies_config['available_ips'] / instance_possible_ips_count))

            instance_config["MinCount"] = instance_per_type_count
            instance_config["MaxCount"] = instance_per_type_count

            subnet_cidr_suffix = get_subnet_cidr_suffix(
                ips_count=proxies_config['available_ips'],
                cidr_suffix_ips_number_mapping=self.cidr_suffix_ips_number_mapping)
            subnet_cidr_block = get_subnet_cidr_block(
                instance_config["CidrBlockFormatting"], 0, subnet_cidr_suffix)

            instance_config["Instances"] = []
            possible_ips_remaining = proxies_config['available_ips']
            for i in range(0, instance_per_type_count):
                instance_config["Instances"].append({
                    "NetworkInterfaces": [],
                    "CidrBlock": subnet_cidr_block,
                    "SubnetCidrSuffix": subnet_cidr_suffix,
                    'GatewayIP': get_vpc_gateway_ip(instance_config["CidrBlockFormatting"])
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

                    instance_config["Instances"][i]["NetworkInterfaces"].append({
                        "uid": "eni-" + str(i) + "-" + str(j),
                        "Ips": {},
                        "Subnet": {
                            "CidrBlock": subnet_cidr_block
                        }

                    })

                    instance_config["Instances"][i]["NetworkInterfaces"][j]["Ips"] = {
                        # Not counting the primary private ip address
                        "SecondaryPrivateIpAddressCount": private_ips_count - 1,
                        # Not counting the primary public ip address
                        "SecondaryPublicIpAddressCount": public_ips_count - 1,
                    }

                    possible_ips_remaining = possible_ips_remaining - \
                        instance_eni_private_ips_count
                    if possible_ips_remaining <= 0:
                        break
            created_instance_type_config = instance_config

            return created_instance_type_config

    def check_image_virtualization_against_instance_types(self, instances_groups_config):
        """Check that an image is supported by instance type

        Args:
            image_id (string): Image type
            instance_type (string): Instance type
        """
        for instance_type_config in instances_groups_config:
            try:
                virtualization_type = self.ec2.Image(
                    instance_type_config["ImageId"]).virtualization_type
                prefix_instance_type = instance_type_config["InstanceType"][:2]

                if ((virtualization_type == "hvm" and prefix_instance_type not in self.hvm_only_instance_types) or
                        (virtualization_type == "paravirtual" and
                            prefix_instance_type in self.hvm_only_instance_types)):
                    raise Exception(
                        "The image {0} with virtualization {1} is not supported by instance type {2}".format(
                            instance_type_config["ImageId"],
                            virtualization_type,
                            instance_type_config["InstanceType"])
                    )
            except Exception as e:
                raise ValueError("Error message {0}".format(e.message))
                break

    @staticmethod
    def __build_base_vpcs_config(instances_config):
        """Build the base vpcs config

        Args:
            instances_config (dict): Instances config

        Returns:
            dict: Base vpcs config
        """
        base_vpcs_config = {}
        for instance_type in instances_config:

            if "VPCCidrBlock" not in instance_type:
                raise ValueError("The instance type config need to have a VPCCidrBlock property")

            if "SecurityGroups" not in instance_type:
                raise ValueError("The instance type config need to have a VPCCidrBlock property")

            base_vpcs_config = {
                "CidrBlock": instance_type["VPCCidrBlock"],
                "CreateInternetGateway": True,
                "Subnets": [],
                "SecurityGroups": instance_type["SecurityGroups"]
            }

            enis_per_subnet = {}
            for instance in instance_type["Instances"]:
                for network_interface in instance["NetworkInterfaces"]:
                    cidr_block = network_interface["Subnet"]["CidrBlock"]

                    subnet_already_exists = False
                    for subnet in base_vpcs_config["Subnets"]:
                        subnet_already_exists = False
                        if subnet["CidrBlock"] == cidr_block:
                            subnet_already_exists = True

                    if cidr_block not in enis_per_subnet:
                        enis_per_subnet[cidr_block] = []

                    enis_per_subnet[cidr_block].append({
                        "uid": network_interface["uid"],
                        "Ips": network_interface["Ips"]
                    })

                    if not subnet_already_exists:
                        base_vpcs_config["Subnets"].append({
                            "CidrBlock": network_interface["Subnet"]["CidrBlock"],
                            "NetworkInterfaces": enis_per_subnet[cidr_block]
                        })

        return base_vpcs_config
