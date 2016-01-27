# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import sys
import logging
import settings


def main():
    """Main
    """

    # Setup logger
    try:  # Python 2.7+
        from logging import NullHandler
    except ImportError:
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass

    logging.getLogger(__name__).addHandler(NullHandler())
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Raise other modules log levels to make the logs for this module less cluttered with noise
    for _ in ("boto3", "botocore"):
        logging.getLogger(_).setLevel(logging.WARNING)

    # Get AWS Session
    try:
        session = aws.get_session('david_dev')
        logger.info('AWS Session created')
    except Exception:
        logger.error('Could not open AWS session')
        sys.exit()

    # Get AWS EC2 Resource
    try:
        ec2 = aws.get_resource(session, 'ec2')
        logger.info('AWS EC2 resource created')
    except Exception as e:
        logger.error('Could not access AWS EC2 resource. Error message %s', e.message)
        sys.exit()

    aws.create_vpcs(ec2, settings.AWS_VPCS)

if __name__ == "__main__":
    main()
