# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class Vpcs(BaseResources):
    """Vpcs representation
    """

    def __init__(self, ec2, ec2_client, tag_base_name, **kwargs):
        """Constructor

        Args:
            ec2 (object): Aws Ec2 session
            ec2_client (object): Aws ec2 session
            tag_base_name (string): Tag base name
            **kwargs: Multiple arguments

        Raises:
            TypeError: Description
        """
        BaseResources.__init__(self, ec2, ec2_client, tag_base_name)
        log_level = kwargs.pop("log_level", logging.WARNING)
        boto_log_level = kwargs.pop("boto_log_level", logging.WARNING)

        if kwargs:
            raise TypeError("Unexpected **kwargs: %r" % kwargs)
        self.logger = setup_logger(__name__, log_level, boto_log_level)

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
