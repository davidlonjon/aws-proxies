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
            self.logger.info("AWS Session created")
        except Exception:
            raise ValueError("Could not open AWS session")

        # Get AWS EC2 Resource
        try:
            self.ec2 = self.__get_resource("ec2")
            self.logger.info("AWS EC2 resource created")
        except Exception as e:
            raise ValueError(
                "Could not create AWS EC2 resource. Error message {0}".format(e.message))

        # Get AWS EC2 Client
        try:
            self.ec2_client = self.__get_client_from_resource(self.ec2)
            self.logger.info("AWS EC2 client created")
        except Exception as e:
            raise ValueError(
                "Could not create AWS EC2 client. Error message {0}".format(e.message))

        self.eni_mappings = kwargs.pop("eni_mappings", None)
        self.cidr_suffix_ips_number_mapping = kwargs.pop(
            "cidr_suffix_ips_number_mapping", None)
        self.proxy_nodes_count = kwargs.pop("proxy_nodes_count", 1)
        self.tag_name_base = kwargs.pop("tag_name_base", "proxies")
        self.hvm_only_instance_types = kwargs.pop(
            "hvm_only_instance_types", [])

        if kwargs:
            raise TypeError("Unexpected **kwargs: %r" % kwargs)

        self.config = {
            "vpcs": {},
            "instance_types": []
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
            resource (object): AWS resource

        Returns:
            object: EC2 resource
        """
        client = resource.meta.client
        return client

    # Taken from
    # http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
    def merge_dicts(self, *dict_args):
        """
        Given any number of dicts, shallow copy and merge into a new dict,
        precedence goes to key value pairs in latter dicts.
        """
        result = {}
        for dictionary in dict_args:
            result.update(dictionary)
        return result

    def merge_config(self, conf1, conf2):
        """Merge cconfig

        Args:
            conf1 (dict): First configuration
            conf2 (dict): Second configuration

        Returns:
            dict: Merge config
        """
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
        return suffix + "-" + i

    def create_name_tag_for_resource(self, resource, tag_name_base, suffix=""):
        """Create a name tag for a EC2 resource using a suffix if passed

        Args:
            resource (object): EC2 resource
            tag_name_base (string): Base name tag value
            suffix (str, optional): Suffix
        """
        tag_name = {
            "Key": "Name",
            "Value": tag_name_base
        }

        if suffix:
            tag_name["Value"] = tag_name["Value"] + "-" + suffix

        resource.create_tags(
            Tags=[tag_name]
        )

    def tag_with_name_with_suffix(self, resource, type, index, tag_base_name):
        suffix = self.create_suffix(type, index)
        self.create_name_tag_for_resource(resource, tag_base_name, suffix)

    def bootstrap_vpcs_infrastructure(self, vpcs):
        """Bootstrap Vpcs infrastructure

        Args:
            vpcs (object): Vpcs base config

        """
        created_vpcs = self.get_or_create_vpcs(vpcs)
        self.config["vpcs"] = created_vpcs

        internet_gateways = self.get_or_create_internet_gateways(self.config[
                                                                 "vpcs"])
        self.config["vpcs"] = self.merge_config(
            self.config["vpcs"], internet_gateways)

        subnets = self.get_or_create_subnets(self.config["vpcs"])
        self.config["vpcs"] = self.merge_config(self.config["vpcs"], subnets)

        security_groups = self.get_or_create_security_groups(self.config[
                                                             "vpcs"])
        self.config["vpcs"] = self.merge_config(
            self.config["vpcs"], security_groups)

        route_tables = self.get_or_create_route_tables(self.config["vpcs"])
        self.config["vpcs"] = self.merge_config(
            self.config["vpcs"], route_tables)

        self.associate_subnets_to_routes(self.config["vpcs"])
        self.create_ig_route(self.config["vpcs"])

        network_acls = self.get_or_create_network_acls(self.config["vpcs"])
        self.config["vpcs"] = self.merge_config(
            self.config["vpcs"], network_acls)

    def get_or_create_vpcs(self, vpcs):
        """Get or create AWS vpcs

        Args:
            ec2 (object): EC2 resource
            vpcs (dict): Vpcs config

        Returns:
            dict: vpcs configs
        """

        created_resources = {}
        for index, vpc in enumerate(vpcs):
            found_resources = self.filter_resources(
                self.ec2.vpcs, "cidrBlock", vpc["CidrBlock"])

            if not found_resources:
                resource = self.ec2.create_vpc(CidrBlock=vpc["CidrBlock"])
            else:
                resource = self.ec2.Vpc(found_resources[0].id)

            self.logger.info("A vpc with ID '%s' and cidr block '%s' has been created or already exists",
                             resource.vpc_id,
                             vpc["CidrBlock"]
                             )

            self.tag_with_name_with_suffix(
                resource, "vpc", index, self.tag_name_base)

            vpc["VpcId"] = resource.vpc_id
            created_resources[resource.vpc_id] = vpc

        return created_resources

    def delete_vpcs(self, vpcs):
        """Delete VPCs

        Args:
            vpcs (dict): Vpcs config
        """
        for vpc_id, vpc in vpcs.iteritems():
            found_vpcs = self.filter_resources(
                self.ec2.vpcs, "cidrBlock", vpc["CidrBlock"])

            if found_vpcs:
                for found_vpc in found_vpcs:
                    self.ec2.Vpc(found_vpc.id).delete()
                    self.logger.error("The vpc with ID '%s' has been deleted",
                                      found_vpc.id
                                      )
            else:
                self.logger.error("No vpc(s) were deleted")

    def get_or_create_internet_gateways(self, vpcs):
        """Get or create internet gateways

        Args:
            ec2 (object): EC2 resource
            vpcs (dict): Vpcs config

        Returns:
            dict: Internet gateways config
        """
        created_resources = []
        index = 0
        for vpc_id, vpc in vpcs.iteritems():
            if "CreateInternetGateway" in vpc:
                found_resources = self.filter_resources(
                    self.ec2.internet_gateways, "attachment.vpc-id", vpc["VpcId"])

                if not found_resources:
                    resource = self.ec2.create_internet_gateway()
                    self.ec2.Vpc(vpc["VpcId"]).attach_internet_gateway(
                        InternetGatewayId=resource.id,
                    )
                else:
                    resource = self.ec2.InternetGateway(found_resources[0].id)

                    for attachment in resource.attachments:
                        vpc_already_attached = False
                        if attachment["VpcId"] == vpc["VpcId"]:
                            vpc_already_attached = True

                        if not vpc_already_attached:
                            self.ec2.Vpc(vpc["VpcId"]).attach_internet_gateway(
                                InternetGatewayId=resource.id,
                            )

                self.tag_with_name_with_suffix(
                    resource, "ig", index, self.tag_name_base)

                self.logger.info(
                    "An internet gateway with ID '%s' attached to vpc '%s' has been created or already exists",
                    resource.id,
                    vpc["VpcId"]
                )

                created_resources.append(
                    {
                        "InternetGatewayId": resource.id,
                    }
                )

                index = index + 1

        return {
            vpc["VpcId"]: {
                "InternetGateways": created_resources
            }
        }

    def get_or_create_subnets(self, vpcs):
        """Get or create subnets

        Args:
            vpcs (object): Vpcs config

        Returns:
            object: Subnets config
        """
        created_resources = []
        for vpc_id, vpc in vpcs.iteritems():
            if "Subnets" in vpc:
                for index, subnet in enumerate(vpc["Subnets"]):
                    found_resources = self.filter_resources(
                        self.ec2.subnets, "cidrBlock", subnet["CidrBlock"])

                    if not found_resources:
                        resource = self.ec2.create_subnet(
                            VpcId=vpc["VpcId"], CidrBlock=subnet["CidrBlock"])
                    else:
                        resource = self.ec2.Subnet(found_resources[0].id)

                        self.logger.info(
                            "A subnet with ID '%s', " +
                            "cidr block '%s' and attached to vpc '%s' has been created or already exists",
                            resource.id,
                            subnet["CidrBlock"],
                            vpc["VpcId"]
                        )

                    self.tag_with_name_with_suffix(
                        resource, "subnet", index, self.tag_name_base)

                    created_resources.append(
                        {
                            "SubnetId": resource.id,
                            "CidrBlock": subnet["CidrBlock"],
                            "NetworkInterfaces": subnet["NetworkInterfaces"]
                        }
                    )

        return {
            vpc["VpcId"]: {
                "Subnets": created_resources
            }
        }

        return created_resources

    def get_or_create_security_groups(self, vpcs):
        """Get or create security groups

        Args:
            vpcs (object): Vpcs config

        Returns:
            object: Security group config
        """
        created_resources = []
        for vpc_id, vpc in vpcs.iteritems():
            if "SecurityGroups" in vpc:
                for index, sg in enumerate(vpc["SecurityGroups"]):
                    found_resources = self.filter_resources(
                        self.ec2.security_groups, "vpc-id", vpc["VpcId"])

                    if not found_resources:
                        resource = self.ec2.create_security_group(
                            VpcId=vpc["VpcId"],
                            GroupName=sg["GroupName"],
                            Description=sg["Description"])

                    else:
                        resource = self.ec2.SecurityGroup(
                            found_resources[0].id)

                    if "IngressRules" in sg:
                        self.authorize_sg_ingress_rules(resource, sg)

                    if "EgressRules" in sg:
                        self.authorize_sg_egress_rules(resource, sg)

                    self.logger.info(
                        "A security group with group name '%s', " +
                        "with ID '%s' and attached to vpc '%s' has been created or already exists",
                        sg["GroupName"],
                        resource.id,
                        vpc["VpcId"]
                    )

                    self.tag_with_name_with_suffix(
                        resource, "sg", index, self.tag_name_base)

                    created_resources.append(
                        {
                            "SecurityGroupId": resource.id,
                            "GroupName": sg["GroupName"],
                            "Description": sg["Description"],
                        }
                    )

        return {
            vpc["VpcId"]: {
                "SecurityGroups": created_resources
            }
        }

        return created_resources

    def authorize_sg_ingress_rules(self, sg, sg_config):
        """Authorize security group ingress (inbound) rules

        Args:
            sg (object): Security group resource
            sg_config (dict): Security group config
        """
        for ingress_rule in sg_config["IngressRules"]:
            for permission in sg.ip_permissions:
                rule_exists = False
                if (ingress_rule["IpProtocol"] == permission.get("IpProtocol", None) and
                        ingress_rule["FromPort"] == permission.get("FromPort", None) and
                        ingress_rule["ToPort"] == permission.get("ToPort", None) and
                        ingress_rule["IpRanges"] == permission.get("IpRanges", None)):
                    rule_exists = True
                    break

            if not rule_exists:
                sg.authorize_ingress(
                    IpPermissions=[ingress_rule])

    def authorize_sg_egress_rules(self, sg, sg_config):
        """Authorize security group egress (outbound) rules

        Args:
            sg (object): Security group resource
            sg_config (dict): Security group config
        """
        for egress_rule in sg_config["EgressRules"]:
            for permission in sg.ip_permissions_egress:
                rule_exists = False
                if (egress_rule["IpProtocol"] == permission.get("IpProtocol", None) and
                        egress_rule["FromPort"] == permission.get("FromPort", None) and
                        egress_rule["ToPort"] == permission.get("ToPort", None) and
                        egress_rule["IpRanges"] == permission.get("IpRanges", None)):
                    rule_exists = True
                    break

            if not rule_exists:
                sg.authorize_egress(
                    IpPermissions=[egress_rule])

    def get_or_create_route_tables(self, vpcs):
        """Get or create route tables

        Args:
            vpcs (object): Vpcs config

        Returns:
            object: Route tables config
        """
        created_resources = []
        index = 0
        for vpc_id, vpc in vpcs.iteritems():
            found_resources = self.filter_resources(
                self.ec2.route_tables, "vpc-id", vpc_id)

            if not found_resources:
                resource = self.ec2.create_route_table(VpcId=vpc_id)
            else:
                resource = self.ec2.RouteTable(found_resources[0].id)

                self.logger.info(
                    "A route table " +
                    "with ID '%s' and attached to pvc '%s' has been created or already exists",
                    resource.id,
                    vpc_id
                )

            self.tag_with_name_with_suffix(
                resource, "rt", index, self.tag_name_base)

            created_resources.append(
                {
                    "RouteTableId": resource.id
                }
            )

            index = index + 1
        return {
            vpc["VpcId"]: {
                "RouteTables": created_resources
            }
        }

    def associate_subnets_to_routes(self, vpcs):
        """Associate subnets to routes

        Args:
            vpcs (dict): Vpcs config
        """
        for vpc_id, vpc in vpcs.iteritems():
            for route in vpc["RouteTables"]:
                route_resource = self.ec2.RouteTable(route["RouteTableId"])

                for subnet in vpc["Subnets"]:
                    found_associations = self.filter_resources(
                        self.ec2.route_tables, "association.subnet-id", subnet["SubnetId"])
                    if not found_associations:
                        route_resource.associate_with_subnet(
                            SubnetId=subnet["SubnetId"])

    def create_ig_route(self, vpcs):
        """Create internet gateway route

        Args:
            vpcs (dict): Vpcs config
        """
        for vpc_id, vpc in vpcs.iteritems():
            for route in vpc["RouteTables"]:
                resource = self.ec2.RouteTable(route["RouteTableId"])
                for route in resource.routes:
                    route_exists = False
                    for ig in vpc["InternetGateways"]:
                        route_exists = False
                        if ig["InternetGatewayId"] == route["GatewayId"]:
                            route_exists = True
                            break
                        if not route_exists:
                            resource.create_route(
                                DestinationCidrBlock="0.0.0.0/0",
                                GatewayId=ig["InternetGatewayId"],
                            )

    def get_or_create_network_acls(self, vpcs):
        """Get or create network acls

        Args:
            vpcs (object): Vpcs config

        Returns:
            object: Network acl config
        """
        created_resources = []
        index = 0
        for vpc_id, vpc in vpcs.iteritems():
            found_resources = self.filter_resources(
                self.ec2.network_acls, "vpc-id", vpc_id)

            if not found_resources:
                resource = self.ec2.create_network_acl(
                    VpcId=vpc_id
                )

                resource.id
            else:
                resource = self.ec2.NetworkAcl(found_resources[0].id)

                self.logger.info(
                    "A network acl " +
                    "with ID '%s' and attached to pvc '%s' has been created or already exists",
                    resource.id,
                    vpc_id
                )

            self.tag_with_name_with_suffix(
                resource, "netacl", index, self.tag_name_base)

            created_resources.append(
                {
                    "NetworkAclId": resource.id,
                }
            )

            index = index + 1
        return {
            vpc["VpcId"]: {
                "NetworkAcls": created_resources
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
        subnet_cidr_block = cidr_block_formatting.replace(
            "\\", "").format(instance_index, 0) + subnet_suffix
        return subnet_cidr_block

    def bootstrap_instances_infrastucture(self, instance_types_config):
        created_instance_types_config = self.setup_instance_types_config(
            instance_types_config)

        self.config["instance_types"].append(created_instance_types_config)

        self.check_image_virtualization_against_instance_types(
            self.config["instance_types"])

        tmp_vpcs_config = self.build_tmp_vpcs_config(instance_types_config)

        # Create VPCS Infrastructure
        self.bootstrap_vpcs_infrastructure([tmp_vpcs_config])

        # Create network interfaces
        self.create_network_interfaces(self.config["vpcs"])

    def setup_instance_types_config(self, instances_config):
        created_instance_type_config = []
        for instance_config in instances_config:
            if "ImageName" in instance_config:
                image_id = self.get_image_id_from_name(
                    instance_config["ImageName"])
                instance_config["ImageId"] = image_id
            elif "ImageId" in instance_config:
                image_id = instance_config["ImageId"]

            instance_enis_count = 1
            instance_eni_private_ips_count = 1
            instance_eni_public_ips_count = 1
            instance_eni_mapping = self.get_instance_eni_mapping(
                instance_config["InstanceType"])
            if instance_eni_mapping:
                instance_enis_count = instance_eni_mapping[0][1]
                instance_eni_private_ips_count = instance_eni_mapping[0][2]
                instance_eni_public_ips_count = instance_eni_mapping[0][2]

            # print "instance_enis_count: {0}".format(instance_enis_count)
            # print "instance_eni_private_ips_count: {0}".format(instance_eni_private_ips_count)
            # print "instance_eni_public_ips_count:
            # {0}".format(instance_eni_public_ips_count)

            instance_possible_ips_count = instance_eni_private_ips_count * \
                instance_enis_count

            # print "instance_possible_ips_count: {0}".format(instance_possible_ips_count)
            # print "self.proxy_nodes_count: {0}".format(self.proxy_nodes_count)
            # subnets_count = instance_enis_count
            # print "subnets_count: {0}".format(subnets_count)
            instance_per_type_count = int(
                math.ceil(self.proxy_nodes_count / instance_possible_ips_count))

            # print "instance_per_type_count:
            # {0}".format(instance_per_type_count)
            instance_config["MinCount"] = instance_per_type_count
            instance_config["MaxCount"] = instance_per_type_count

            subnet_cidr_suffix = self.get_subnet_cidr_suffix(
                self.proxy_nodes_count)
            subnet_cidr_block = self.get_subnet_cidr_block(
                instance_config["CidrBlockFormatting"], 0, subnet_cidr_suffix)

            # print "*****"
            # print "subnet_cidr_suffix: {0}".format(subnet_cidr_suffix)

            instance_config["Instances"] = []
            possible_ips_remaining = self.proxy_nodes_count
            for i in range(0, instance_per_type_count):
                instance_config["Instances"].append({
                    "NetworkInterfaces": [],
                    "CidrBlock": subnet_cidr_block
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

    def check_image_virtualization_against_instance_types(self, instance_types_config):
        """Check that an image is supported by instance type

        Args:
            image_id (string): Image type
            instance_type (string): Instance type
        """
        for instance_type_config in instance_types_config:
            try:
                virtualization_type = self.ec2.Image(
                    instance_type_config["ImageId"]).virtualization_type
                virtualization_type = 'hvm'
                prefix_instance_type = instance_type_config["InstanceType"][:2]

                if ((virtualization_type == "hvm" and prefix_instance_type not in self.hvm_only_instance_types) or
                        (virtualization_type == "paravirtual" and prefix_instance_type in self.hvm_only_instance_types)):
                    raise Exception(
                        "The image {0} with virtualization {1} is not supported by instance type {2}".format(
                            instance_type_config["ImageId"],
                            virtualization_type,
                            instance_type_config["InstanceType"])
                    )
            except Exception as e:
                raise ValueError("Error message {0}".format(e.message))
                break

    def build_tmp_vpcs_config(self, instance_types_config):
        """Build a temporary vpcs config schema

        Args:
            instance_types_config (dict): Instance types config

        Returns:
            dict: temporary vpcs config
        """
        tmp_vpcs_config = {}
        for instance_type in instance_types_config:

            if "VPCCidrBlock" not in instance_type:
                self.logger.error(
                    "ERROR: The instance type config need to have a VPCCidrBlock property")
                sys.exit()

            if "SecurityGroups" not in instance_type:
                self.logger.error(
                    "ERROR: The instance type config need to have a SecurityGroups property")
                sys.exit()

            tmp_vpcs_config = {
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
                    for subnet in tmp_vpcs_config["Subnets"]:
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
                        tmp_vpcs_config["Subnets"].append({
                            "CidrBlock": network_interface["Subnet"]["CidrBlock"],
                            "NetworkInterfaces": enis_per_subnet[cidr_block]
                        })

        return tmp_vpcs_config

    def create_network_interfaces(self, vpcs):
        """Create network interfaces

        Args:
            vpcs (dict): Vpcs config
        """
        for vpc_id, vpc in vpcs.iteritems():
            index = 0
            for subnet in vpc["Subnets"]:
                aws_subnet = self.ec2.Subnet(subnet["SubnetId"])
                for eni in subnet["NetworkInterfaces"]:
                    found_eni = self.filter_resources(
                        aws_subnet.network_interfaces, "tag-value", eni["uid"])
                    if not found_eni:
                        created_eni = aws_subnet.create_network_interface(
                            SecondaryPrivateIpAddressCount=eni["Ips"][
                                "SecondaryPrivateIpAddressCount"],
                        )
                        self.tag_with_name_with_suffix(
                            created_eni, "eni", index, self.tag_name_base)

                        created_eni.create_tags(
                            Tags=[{
                                "Key": "uid",
                                "Value": eni["uid"]
                            }]
                        )
                        index = index + 1

                    self.logger.info("A network interface '%s' for subnet '%s' has been created or already exists",
                                     eni["uid"],
                                     subnet["SubnetId"]
                                     )

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
            if default is not None and choice == "":
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
            "Name": filter_name,
            "Values": values
        }]

        return list(function.filter(Filters=filters))
