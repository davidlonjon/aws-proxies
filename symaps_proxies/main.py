# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import settings
# import json


def main():
    """Main
    """

    AWSEC2Interface = aws.AWSEC2Interface(
        'david_dev',
        eni_mappings=settings.AWS_ENI_MAPPINGS,
        cidr_suffix_ips_number_mapping=settings.CIDR_SUFFIX_IPS_NUMBER_MAPPING,
        proxy_nodes_count=settings.PROXY_NODES_COUNT
    )

    # # Create VPCS
    vpcs = AWSEC2Interface.create_vpcs(settings.AWS_VPCS)
    config = vpcs

    # Create Internet Gateways associated to VPCs
    internet_gateways = AWSEC2Interface.create_internet_gateways(vpcs)
    config = AWSEC2Interface.merge_config(config, internet_gateways)

    # Create subnets
    subnets = AWSEC2Interface.create_subnets(vpcs)
    config = AWSEC2Interface.merge_config(config, subnets)

    # Create Security groups
    security_groups = AWSEC2Interface.create_security_groups(vpcs)
    config = AWSEC2Interface.merge_config(config, security_groups)

    # with open(settings.AWS_CONFIG_FILE, 'w') as fp:
    #     print json.dump(config, fp)

    AWSEC2Interface.create_instances(settings.AWS_INSTANCES)
if __name__ == "__main__":
    main()
