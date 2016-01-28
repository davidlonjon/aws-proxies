# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import settings
import json


def main():
    """Main
    """

    AWSEC2Interface = aws.AWSEC2Interface('david_dev')

    # Create VPCS
    vpcs = AWSEC2Interface.create_vpcs(settings.AWS_VPCS)
    config = vpcs

    # Create Internet Gateways associated to VPCs
    internet_gateways = AWSEC2Interface.create_internet_gateways(vpcs)
    config = AWSEC2Interface.merge_config(config, internet_gateways)

    # Create  subnets
    subnets = AWSEC2Interface.create_subnets(vpcs)
    config = AWSEC2Interface.merge_config(config, subnets)

    print config
    with open(settings.AWS_CONFIG_FILE, 'w') as fp:
        print json.dump(config, fp)


if __name__ == "__main__":
    main()
