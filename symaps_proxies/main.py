# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import settings


def main():
    """Main
    """

    AWSEC2Interface = aws.AWSEC2Interface('david_dev')

    # Create VPCS
    vpcs = AWSEC2Interface.create_vpcs(settings.AWS_VPCS)

    # Create Internet Gateways associated to VPCs
    internet_gateways = AWSEC2Interface.create_internet_gateways(vpcs)

    print internet_gateways

if __name__ == "__main__":
    main()
