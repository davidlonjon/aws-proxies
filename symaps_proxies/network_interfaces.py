# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class NetworkInterfaces(BaseResources):
    """Network interfaces representation
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

    def create(self, config):
        """Create network interfaces

        Args:
            config (dict): Vpcs config
        """
        for vpc_id, vpc_config in config.iteritems():
            index = 0
            for subnet in vpc_config["Subnets"]:
                aws_subnet = self.ec2.Subnet(subnet["SubnetId"])
                for eni in subnet["NetworkInterfaces"]:
                    found_eni = filter_resources(
                        aws_subnet.network_interfaces, "tag-value", eni["uid"])
                    if not found_eni:
                        created_eni = aws_subnet.create_network_interface(
                            SecondaryPrivateIpAddressCount=eni["Ips"][
                                "SecondaryPrivateIpAddressCount"],
                        )
                        tag_with_name_with_suffix(
                            created_eni, "eni", index, self.tag_base_name)

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

    def associate_public_ips_to_enis(self):
        """Associate public ips to elastic network interfaces
        """
        aws_enis = list(
            self.ec2.network_interfaces.filter(
                Filters=[
                    {
                        "Name": "tag:Name",
                        "Values": [self.tag_base_name + '-*']
                    }
                ]
            )
        )

        for aws_eni in aws_enis:
            for aws_private_ip_address in aws_eni.private_ip_addresses:
                msg = "The network interface '{0}' private ip '{1}' has been or is already" \
                    " associated with public ip '{2}'"

                if 'Association' not in aws_private_ip_address:
                    aws_eip_alloc = self.ec2_client.allocate_address(
                        Domain='vpc'
                    )
                    self.ec2_client.associate_address(
                        AllocationId=aws_eip_alloc['AllocationId'],
                        NetworkInterfaceId=aws_eni.id,
                        PrivateIpAddress=aws_private_ip_address['PrivateIpAddress']
                    )

                    msg = msg.format(
                        aws_eni.id,
                        aws_private_ip_address['PrivateIpAddress'],
                        aws_eip_alloc['PublicIp']
                    )
                else:
                    msg = msg.format(
                        aws_eni.id,
                        aws_private_ip_address['PrivateIpAddress'],
                        aws_private_ip_address['Association']['PublicIp']
                    )

                self.logger.info(msg)

    def release_public_ips(self):
        """Dissociate public ips to elastic network interfaces and release ips
        """
        aws_enis = filter_resources(
            self.ec2.network_interfaces, "tag:Name", self.tag_base_name + '-*')

        eni_ids = []
        for aws_eni in aws_enis:
            for aws_private_ip_address in aws_eni.private_ip_addresses:
                eni_ids.append(aws_eni.id)

        aws_addresses = self.ec2_client.describe_addresses(
            Filters=[
                {
                    'Name': 'network-interface-id',
                    'Values': eni_ids
                },
            ],
        )

        for aws_public_ip in aws_addresses['Addresses']:
            self.ec2_client.disassociate_address(
                AssociationId=aws_public_ip['AssociationId']
            )

            self.ec2_client.release_address(
                AllocationId=aws_public_ip['AllocationId'],
            )

            self.logger.info(
                "The public IP '%s' has been dissociated from network interface '%s' and released",
                aws_public_ip['PublicIp'],
                aws_public_ip['NetworkInterfaceId']
            )

    def delete(self):
        """Delete elastic network interfaces
        """
        aws_enis = filter_resources(
            self.ec2.network_interfaces, "tag:Name", self.tag_base_name + '-*')

        for aws_eni in aws_enis:
            if hasattr(aws_eni, 'attachment') and aws_eni.attachment is not None:
                print aws_eni.attachment
                self.ec2_client.detach_network_interface(
                    AttachmentId=aws_eni.attachment['AttachmentId'],
                )

            aws_eni.delete()

            self.logger.info(
                "The network interface '%s' has been detached from instance and deleted",
                aws_eni.id
            )
