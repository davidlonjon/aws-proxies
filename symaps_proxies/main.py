# -*- coding: utf-8 -*-

from aws_proxies import AWSProxies
import logging
import sys

PROXY_NODES_COUNT = 4
INSTANCES_GROUPS_CONFIG = [
    {
        'InstanceType': 't1.micro',
        'ImageName': 'tinyproxy',
        'VPCCidrBlock': '15.0.0.0/16',
        'CidrBlockFormatting': '15.0.\{0\}.\{1\}',
        'SecurityGroups': [
            {
                'GroupName': 'default',
                'Description': 'Security group for proxies',
                'IngressRules': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8888,
                        'ToPort': 8888,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0'
                            },
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                            },
                        ]
                    }
                ]
            }
        ]
    }
]



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
        proxies = AWSProxies(
            profile='david_dev',
            proxy_nodes_count=PROXY_NODES_COUNT,
        )
    except Exception as e:
        logger.error("Error: %s", e.message)
        sys.exit()

    # Create Instances Infrastructure
    proxies.bootstrap_instances_infrastucture(INSTANCES_GROUPS_CONFIG)

if __name__ == "__main__":
    main()
