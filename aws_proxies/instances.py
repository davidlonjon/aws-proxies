# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class Instances(BaseResources):
    """Instances representation
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

    def terminate(self):
        """Terminate instances
        """
        aws_instances_ids = []
        aws_instances = self.ec2.instances.filter(Filters=[
            {
                "Name": "tag:Name",
                "Values": [self.tag_base_name + '-*']
            },
            {
                "Name": "instance-state-name",
                "Values": ['pending', 'running', 'shutting-down', 'stopping', 'stopped']
            },
        ])

        for aws_instance in aws_instances:
            aws_instances_ids.append(aws_instance.id)

        aws_instances_ids_str = str(aws_instances_ids).strip('[]')
        if aws_instances_ids:
            self.logger.info(
                "Terminating instances %s. Please wait",
                aws_instances_ids_str
            )

            self.ec2_client.terminate_instances(
                InstanceIds=aws_instances_ids
            )

            waiter = self.ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=aws_instances_ids)

            self.logger.info(
                "Instances %s are now terminated",
                aws_instances_ids_str
            )

    def get_running_proxies_ips(self, silent=False):
        """Get the public and private ips of all running proxy instances

        Args:
            silent (bool, optional): Silent

        Returns:
            Dict: Dictionnary of tuple public/private ips
        """
        filter = [
            {
                "Name": "tag:Name",
                "Values": [self.tag_base_name + '-*']
            },
            {
                "Name": "instance-state-name",
                "Values": ['running']
            },
        ]

        if not silent:
            print "Waiting for all proxies to be running..."

        waiter = self.ec2_client.get_waiter('instance_running')
        waiter.wait(Filters=filter)

        instances = self.ec2.instances.filter(Filters=filter)
        ips = []
        for instance in list(instances):
            for eni in instance.network_interfaces_attribute:
                for private_ip_addresses in eni['PrivateIpAddresses']:
                    ips.append(
                        (private_ip_addresses['Association']['PublicIp'], private_ip_addresses['PrivateIpAddress'])
                    )

        return ips

    def create(self, instances_groups_config, vpcs_config):
        """Create instances

        Args:
            instances_groups_config (dict): Instances groups config
            vpcs_config (dict): Vpcs config
        """
        instances_config = []
        user_data = "#!/bin/bash\n"
        for instance_group in instances_groups_config:
            for instance_index, instance in enumerate(instance_group['Instances']):
                instance_config = {
                    'ImageId': instance_group['ImageId'],
                    'MinCount': 1,
                    'MaxCount': 1,
                    'InstanceType': instance_group['InstanceType'],
                    'DisableApiTermination': False,
                    'InstanceInitiatedShutdownBehavior': 'terminate',
                    'NetworkInterfaces': [],
                }

                for index, eni in enumerate(instance['NetworkInterfaces']):
                    found_eni = filter_resources(self.ec2.network_interfaces, "tag-value", eni["uid"])
                    if found_eni:
                        instance_config['NetworkInterfaces'].append({
                            'NetworkInterfaceId': found_eni[0].id,
                            'DeviceIndex': index
                        })

                    if index > 0:
                        user_data += "\n\nsudo bash -c \"echo 'auto eth{0}' >> /etc/network/interfaces\"\n" \
                            "sudo bash -c \"echo 'iface eth{0} inet dhcp' >> /etc/network/interfaces\"\n" \
                            "sudo ifup eth{0}\n" \
                            "sudo bash -c \"echo '40{0} eth{0}_rt' >> /etc/iproute2/rt_tables\"\n".format(index)

                    for private_ip_address in found_eni[0].private_ip_addresses:
                        if not private_ip_address['Primary']:
                            user_data += "\n# Add the primary ip address to the network interface\n"
                            user_data += "sudo ip addr add {0}{1} dev eth{2}\n".format(
                                private_ip_address['PrivateIpAddress'], instance['SubnetCidrSuffix'], index
                            )
                        if index > 0:
                            user_data += "\n# Add an ip rule to a routing table\n"
                            user_data += "sudo ip rule add from {0} lookup eth{1}_rt\n".format(
                                private_ip_address['PrivateIpAddress'],
                                index
                            )

                    if index > 0:
                        user_data += "\n# Add a route\n"
                        user_data += "sudo ip route add default via {0} dev " \
                            "eth{1} table eth{1}_rt\n".format(instance['GatewayIP'], index)

                instance_config['UserData'] = user_data

                aws_reservation = self.ec2_client.run_instances(**instance_config)
                aws_instance_config = aws_reservation['Instances'][0]
                aws_instance = self.ec2.Instance(aws_instance_config['InstanceId'])
                tag_with_name_with_suffix(aws_instance, "i", instance_index, self.tag_base_name)
                instance_config['InstanceId'] = aws_instance_config['InstanceId']
                instances_config.append(instance_config)

        return instances_config
