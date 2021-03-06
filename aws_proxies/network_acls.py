# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class NetworkAcls(BaseResources):
    """Network acls representation
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
        """Get or create network acls

        Args:
            config (object): Vpcs config

        Returns:
            object: Network acl config
        """
        created_network_acls = []
        index = 0
        for vpc_id, vpc_config in config.iteritems():
            network_acls = filter_resources(
                self.ec2.network_acls, "vpc-id", vpc_id)

            if not network_acls:
                network_acl = self.ec2.create_network_acl(
                    VpcId=vpc_id
                )

                network_acl.id
            else:
                network_acl = self.ec2.NetworkAcl(network_acls[0].id)

                self.logger.info(
                    "A network acl " +
                    "with ID '%s' and attached to pvc '%s' has been created or already exists",
                    network_acl.id,
                    vpc_id
                )

            tag_with_name_with_suffix(
                network_acl, "netacl", index, self.tag_base_name)

            created_network_acls.append(
                {
                    "NetworkAclId": network_acl.id,
                }
            )

            index = index + 1

        return {
            vpc_config["VpcId"]: {
                "NetworkAcls": created_network_acls
            }
        }

    def delete(self):
        """Delete network acls
        """
        network_acls = filter_resources(
            self.ec2.network_acls,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for network_acl in network_acls:
            if not network_acl.is_default:
                network_acl.delete()
                self.logger.info(
                    "The network acl with ID '%s' has been deleted ",
                    network_acl.id,
                )
