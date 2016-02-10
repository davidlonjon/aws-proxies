# -*- coding: utf-8 -*-


class BaseResources(object):
    """Base aws ec2 resources representation
    """

    def __init__(self, ec2, ec2_client, tag_base_name):
        """Constructor

        Args:
            ec2 (object): Aws Ec2 session
            ec2_client (object): Aws Ec2 client
            tag_base_name (dict): Resource tag base name
        """
        self.ec2 = ec2
        self.ec2_client = ec2_client
        self.tag_base_name = tag_base_name
