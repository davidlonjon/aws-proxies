# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class Subnets(BaseResources):
    """Subnets representation
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
        """Get or create Aws Ec2 subnets

        Args:
            config (dict): Vpcs config

        Returns:
            dict: Subnets configs
        """
        created_subnets = []
        for vpc_id, vpc_config in config.iteritems():
            if "Subnets" in vpc_config:
                for index, subnet_config in enumerate(vpc_config["Subnets"]):
                    subnets = filter_resources(
                        self.ec2.subnets, "cidrBlock", subnet_config["CidrBlock"])

                    if not subnets:
                        subnet = self.ec2.create_subnet(
                            VpcId=vpc_config["VpcId"], CidrBlock=subnet_config["CidrBlock"])
                    else:
                        subnet = self.ec2.Subnet(subnets[0].id)

                    self.logger.info(
                        "A subnet with ID '%s', " +
                        "cidr block '%s' and attached to vpc '%s' has been created or already exists",
                        subnet.id,
                        subnet_config["CidrBlock"],
                        vpc_config["VpcId"]
                    )

                    tag_with_name_with_suffix(
                        subnet, "subnet", index, self.tag_base_name)

                    created_subnets.append(
                        {
                            "SubnetId": subnet.id,
                            "CidrBlock": subnet_config["CidrBlock"],
                            "NetworkInterfaces": subnet_config["NetworkInterfaces"]
                        }
                    )

        return {
            vpc_config["VpcId"]: {
                "Subnets": created_subnets
            }
        }

    def delete(self):
        subnets = filter_resources(
            self.ec2.subnets,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for subnet in subnets:
            subnet.delete()

            self.logger.info(
                "The subnet with ID '%s' has been deleted ",
                subnet.id,
            )
