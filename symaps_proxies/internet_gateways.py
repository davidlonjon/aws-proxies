# -*- coding: utf-8 -*-

from base_resources import BaseResources
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class InternetGateways(BaseResources):
    """Internet gateways representation
    """

    def __init__(self, ec2, ec2_client, tag_base_name):
        BaseResources.__init__(self, ec2, ec2_client, tag_base_name)
        self.logger = setup_logger(__name__)

    def get_or_create(self, config):
        """Get or create internet gateways

        Args:
            config (dict): config config

        Returns:
            dict: Internet gateways config
        """
        created_resources = []
        index = 0
        for vpc_id, vpc_config in config.iteritems():
            if "CreateInternetGateway" in vpc_config:
                internet_gateways = filter_resources(
                    self.ec2.internet_gateways, "attachment.vpc-id", vpc_config["VpcId"])

                if not internet_gateways:
                    internet_gateway = self.ec2.create_internet_gateway()
                    self.ec2.Vpc(vpc_config["VpcId"]).attach_internet_gateway(
                        InternetGatewayId=internet_gateway.id,
                    )
                else:
                    internet_gateway = self.ec2.InternetGateway(internet_gateways[0].id)

                    for attachment in internet_gateway.attachments:
                        vpc_already_attached = False
                        if attachment["VpcId"] == vpc_config["VpcId"]:
                            vpc_already_attached = True

                        if not vpc_already_attached:
                            self.ec2.Vpc(vpc_config["VpcId"]).attach_internet_gateway(
                                InternetGatewayId=internet_gateway.id,
                            )

                tag_with_name_with_suffix(
                    internet_gateway, "ig", index, self.tag_base_name)

                self.logger.info(
                    "An internet gateway with ID '%s' attached to vpc '%s' has been created or already exists",
                    internet_gateway.id,
                    vpc_config["VpcId"]
                )

                created_resources.append(
                    {
                        "InternetGatewayId": internet_gateway.id,
                    }
                )

                index = index + 1

        return {
            vpc_config["VpcId"]: {
                "InternetGateways": created_resources
            }
        }

    def delete(self):
        """Delete internet gateways
        """
        internet_gateways = filter_resources(
            self.ec2.internet_gateways,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for internet_gateway in internet_gateways:
            if hasattr(internet_gateway, 'attachments'):
                for attachment in internet_gateway.attachments:
                    internet_gateway.detach_from_vpc(VpcId=attachment['VpcId'])

            internet_gateway.delete()

            self.logger.info(
                "The internet_gateway with ID '%s' has been deleted ",
                internet_gateway.id,
            )
