# -*- coding: utf-8 -*-

from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class Vpcs(object):
    """VPCS representation
    """

    def __init__(self, ec2, tag_base_name):
        """Constructor

        Args:
            ec2 (object): Aws Ec2 session
            tag_base_name (dict): Resource tag base name
        """
        self.logger = setup_logger(__name__)
        self.ec2 = ec2
        self.tag_base_name = tag_base_name

    def get_or_create(self, config):
            """Get or create Aws Ec2 vpcs

            Args:
                config (dict): Vpcs config

            Returns:
                dict: vpcs configs
            """

            created_vpcs = {}
            for index, vpc_config in enumerate(config):
                vpcs = filter_resources(
                    self.ec2.vpcs, "cidrBlock", vpc_config["CidrBlock"])

                if not vpcs:
                    vpc = self.ec2.create_vpc(CidrBlock=vpc_config["CidrBlock"])
                else:
                    vpc = self.ec2.Vpc(vpcs[0].id)

                self.logger.info("A vpc with ID '%s' and cidr block '%s' has been created or already exists",
                                 vpc.vpc_id,
                                 vpc_config["CidrBlock"]
                                 )

                tag_with_name_with_suffix(
                    vpc, "vpc", index, self.tag_base_name)

                vpc_config["VpcId"] = vpc.vpc_id
                created_vpcs[vpc.vpc_id] = vpc_config

            return created_vpcs

    def delete(self):
        """Delete Vpcs
        """
        vpcs = filter_resources(
            self.ec2.vpcs,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for vpc in vpcs:
            vpc.delete()

            self.logger.info(
                "The vpc with ID '%s' has been deleted ",
                vpc.id,
            )
