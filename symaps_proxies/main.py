# -*- coding: utf-8 -*-

from aws_proxies import AWSProxies
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
        proxies = AWSProxies(
            profile='david_dev',
            proxy_nodes_count=settings.PROXY_NODES_COUNT,
        )
    except Exception as e:
        logger.error("Error: %s", e.message)
        sys.exit()

    # Create Instances Infrastructure
    proxies.bootstrap_instances_infrastucture(settings.INSTANCES_GROUPS_CONFIG)

if __name__ == "__main__":
    main()
