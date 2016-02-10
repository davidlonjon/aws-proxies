# -*- coding: utf-8 -*-

from base_resources import BaseResources
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class SecurityGroups(BaseResources):
    """Security groups representation
    """

    def __init__(self, ec2, ec2_client, tag_base_name):
        BaseResources.__init__(self, ec2, ec2_client, tag_base_name)
        self.logger = setup_logger(__name__)

    def get_or_create(self, config):
        """Get or create Aws Ec2 security groups

        Args:
            config (dict): Vpcs config

        Returns:
            dict: Security groups configs
        """

        created_security_groups = []
        for vpc_id, vpc_config in config.iteritems():
            if "SecurityGroups" in vpc_config:
                for index, sg in enumerate(vpc_config["SecurityGroups"]):
                    security_groups = filter_resources(
                        self.ec2.security_groups, "vpc-id", vpc_config["VpcId"])

                    if not security_groups:
                        resource = self.ec2.create_security_group(
                            VpcId=vpc_config["VpcId"],
                            GroupName=sg["GroupName"],
                            Description=sg["Description"])

                    else:
                        resource = self.ec2.SecurityGroup(
                            security_groups[0].id)

                    if "IngressRules" in sg:
                        self.authorize_sg_ingress_rules(resource, sg)

                    if "EgressRules" in sg:
                        self.authorize_sg_egress_rules(resource, sg)

                    self.logger.info(
                        "A security group with group name '%s', " +
                        "with ID '%s' and attached to vpc '%s' has been created or already exists",
                        sg["GroupName"],
                        resource.id,
                        vpc_config["VpcId"]
                    )

                    tag_with_name_with_suffix(
                        resource, "sg", index, self.tag_base_name)

                    created_security_groups.append(
                        {
                            "SecurityGroupId": resource.id,
                            "GroupName": sg["GroupName"],
                            "Description": sg["Description"],
                        }
                    )

        return {
            vpc_config["VpcId"]: {
                "SecurityGroups": created_security_groups
            }
        }

        return created_security_groups

    def delete(self):
        """Delete security groups
        """
        security_groups = filter_resources(
            self.ec2.security_groups,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for security_group in security_groups:
            if "default" != security_group.group_name:
                security_group.delete()
                self.logger.info(
                    "The security group with ID '%s' has been deleted ",
                    security_group.id,
                )

    @staticmethod
    def authorize_sg_ingress_rules(sg, sg_config):
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

    @staticmethod
    def authorize_sg_egress_rules(sg, sg_config):
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
