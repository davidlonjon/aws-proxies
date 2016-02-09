# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import logging
import settings
import sys


def setup_logger():
        """Setup logger

        Returns:
            object: Logger
        """
        try:  # Python 2.7+
            from logging import NullHandler
        except ImportError:
            class NullHandler(logging.Handler):

                def emit(self, record):
                    pass

        logging.getLogger(__name__).addHandler(NullHandler())
        logging.basicConfig(level=logging.INFO)

        # Raise other modules log levels to make the logs for this module less
        # cluttered with noise
        for _ in ("boto3", "botocore"):
            logging.getLogger(_).setLevel(logging.WARNING)

        return logging.getLogger(__name__)


def main():
    """Main
    """

    logger = setup_logger()

    try:
        AWSEC2Interface = aws.AWSEC2Interface(
            profile='david_dev',
            eni_mappings=settings.AWS_ENI_MAPPINGS,
            cidr_suffix_ips_number_mapping=settings.CIDR_SUFFIX_IPS_NUMBER_MAPPING,
            proxy_nodes_count=settings.PROXY_NODES_COUNT,
            tag_name_base=settings.AWS_TAG_NAME_BASE,
            hvm_only_instance_types=settings.AWS_HVM_ONLY_INSTANCE_TYPES
        )
    except ValueError as e:
        logger.error("Error: %s", e.message)
        sys.exit()

    # Create Instances Infrastructure
    AWSEC2Interface.bootstrap_instances_infrastucture(settings.AWS_INSTANCES_GROUPS_CONFIG)

if __name__ == "__main__":
    main()
