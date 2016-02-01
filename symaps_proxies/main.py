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

    # Create VPCS
    AWSEC2Interface.bootstrap_vpcs_infrastructure(settings.AWS_VPCS)

    print AWSEC2Interface.config
    # with open(settings.AWS_CONFIG_FILE, 'w') as fp:
    #     print json.dump(config, fp)

    # AWSEC2Interface.create_instances(settings.AWS_INSTANCES)
if __name__ == "__main__":
    main()
