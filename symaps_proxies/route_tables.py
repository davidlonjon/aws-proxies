# -*- coding: utf-8 -*-

from base_resources import BaseResources
import logging
from utils import setup_logger, filter_resources, tag_with_name_with_suffix


class RouteTables(BaseResources):
    """Route Tables representation
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
        """Get or create route tables

        Args:
            config (dict): Vpcs config

        Returns:
            dict: Security groups configs
        """

        created_route_tables = []
        index = 0
        for vpc_id, vpc_config in config.iteritems():
            route_tables = filter_resources(
                self.ec2.route_tables, "vpc-id", vpc_id)

            if not route_tables:
                route_table = self.ec2.create_route_table(VpcId=vpc_id)
            else:
                route_table = self.ec2.RouteTable(route_tables[0].id)

                self.logger.info(
                    "A route table " +
                    "with ID '%s' and attached to vpc '%s' has been created or already exists",
                    route_table.id,
                    vpc_id
                )

            tag_with_name_with_suffix(
                route_table, "rt", index, self.tag_base_name)

            created_route_tables.append(
                {
                    "RouteTableId": route_table.id
                }
            )

            index = index + 1
        return {
            vpc_config["VpcId"]: {
                "RouteTables": created_route_tables
            }
        }

    def delete(self):
        """Delete route tables
        """
        route_tables = filter_resources(
            self.ec2.route_tables,
            "tag:Name",
            self.tag_base_name + '-*'
        )

        for route_table in route_tables:
            is_main_route_table = True
            if hasattr(route_table, 'associations'):
                for association in route_table.associations.all():
                    if not association.main:
                        is_main_route_table = False
                        self.ec2_client.disassociate_route_table(
                            AssociationId=association.id
                        )

                        self.logger.info(
                            "The route table association with ID '%s' has been deleted",
                            association.id,
                        )

            for route in route_table.routes:
                if 'local' != route['GatewayId']:
                    self.ec2_client.delete_route(
                        RouteTableId=route_table.id,
                        DestinationCidrBlock=route['DestinationCidrBlock']
                    )

                    self.logger.info(
                        "The route for gateway ID '%s' with cird block '%s' and " +
                        "associated to route table '%s' has been deleted",
                        route['GatewayId'],
                        route['DestinationCidrBlock'],
                        route_table.id
                    )

            if not is_main_route_table:
                route_table.delete()
                self.logger.info(
                    "The route table with ID '%s' has been deleted",
                    route_table.id
                )

    def associate_subnets_to_routes(self, config):
        """Associate subnets to routes

        Args:
            config (dict): Vpcs config
        """
        for vpc_id, vpc_config in config.iteritems():
            for route in vpc_config["RouteTables"]:
                route_resource = self.ec2.RouteTable(route["RouteTableId"])

                for subnet in vpc_config["Subnets"]:
                    found_associations = filter_resources(
                        self.ec2.route_tables, "association.subnet-id", subnet["SubnetId"])
                    if not found_associations:
                        route_resource.associate_with_subnet(
                            SubnetId=subnet["SubnetId"])

    def create_ig_route(self, config):
        """Create internet gateway route

        Args:
            config (dict): Vpcs config
        """
        for vpc_id, vpc_config in config.iteritems():
            for route in vpc_config["RouteTables"]:
                resource = self.ec2.RouteTable(route["RouteTableId"])
                for route in resource.routes:
                    route_exists = False
                    for ig in vpc_config["InternetGateways"]:
                        route_exists = False
                        if ig["InternetGatewayId"] == route["GatewayId"]:
                            route_exists = True
                            break
                        if not route_exists:
                            resource.create_route(
                                DestinationCidrBlock="0.0.0.0/0",
                                GatewayId=ig["InternetGatewayId"],
                            )
