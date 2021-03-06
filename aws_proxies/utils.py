# -*- coding: utf-8 -*-

import logging
import sys


def setup_logger(name, level=logging.WARNING, boto_logging_level=logging.WARNING):
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

        logging.getLogger(name).addHandler(NullHandler())

        # Raise other modules log levels to make the logs for this module less
        # cluttered with noise
        for _ in ("boto3", "botocore"):
            logging.getLogger(_).setLevel(boto_logging_level)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        return logger


def create_suffix(suffix, index):
        """Create suffix using an index

        Args:
            suffix (string): Base suffix
            index (int/string): Index

        Returns:
            string: Suffic
        """
        i = "%02d" % (int(index) + 1,)
        return suffix + "-" + i


# Taken from:
# http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def confirm_proxies_and_infra_creation(instance_group_config, available_ips):
    """Ask confirmation to create proxies and vpc infrastructure

    Args:
        instance_group_config (dict): Instance group config
        available_ips (integer): Available ips

    Returns:
        boolean: Answer
    """
    instances_message = []
    for instances_group in instance_group_config:
        instances_message.append(
            "{0} x {1} instance(s)".format(instances_group['MaxCount'], instances_group['InstanceType'])
        )
    instances_message_string = ' and '.join(instances_message)
    question = "\n{0} bound to a total of {1} elastic ip(s) will be created.\n" \
        "Also a new vpc with dependent resources will be created.\n" \
        "Do you want to continue?".format(instances_message_string, available_ips)

    return query_yes_no(question)


def confirm_proxies_and_infra_deletion(tag_base_name):
    """Ask confirmation to delete proxies and vpc infrastructure

    Args:
        tag_base_name (string): tag base name

    Returns:
        boolean: Answer
    """
    question = "\nAll existing proxies instances tagged '{0}' will be terminated, publics ips released " \
        "and every ec2 resources tagged '{0}' will also be deleted.\n" \
        "Do you want to continue?".format(tag_base_name)

    return query_yes_no(question)


# Taken from
# http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def merge_config(conf1, conf2):
    """Merge cconfig

    Args:
        conf1 (dict): First configuration
        conf2 (dict): Second configuration

    Returns:
        dict: Merge config
    """
    new_conf = {}
    for key, value in conf2.iteritems():
        if key in conf1:
            new_conf[key] = merge_dicts(conf1[key], value)

    return new_conf


def filter_resources(resource, filter_name, filter_value):
        """Filter AWS resources

        Args:
            resource (object): EC2 resource
            filter_name (string): Filter name
            filter_value (string/list): Filter value(s)

        Returns:
            List: Filtered AWS resources
        """
        values = [filter_value]
        if type(filter_value) is list:
            values = filter_value

        filters = [{
            "Name": filter_name,
            "Values": values
        }]

        return list(resource.filter(Filters=filters))


def create_name_tag_for_resource(resource, tag_base_name, suffix=""):
        """Create a name tag for a EC2 resource using a suffix if passed

        Args:
            resource (object): EC2 resource
            tag_base_name (string): Tag base name
            suffix (string, optional): Suffix
        """
        tag_name = {
            "Key": "Name",
            "Value": tag_base_name
        }

        if suffix:
            tag_name["Value"] = tag_name["Value"] + "-" + suffix

        resource.create_tags(
            Tags=[tag_name]
        )


def tag_with_name_with_suffix(resource, type, index, tag_base_name):
    """Tag EC2 resource using name with a suffix

    Args:
        resource (object): EC2 resource
        type (string): Resource type
        index (integer): Resource index number
        tag_base_name (string): Tag base name
    """
    suffix = create_suffix(type, index)
    create_name_tag_for_resource(resource, tag_base_name, suffix)


def get_subnet_cidr_block(cidr_block_formatting, instance_index, subnet_suffix):
    """Get subnet cidr block

    Args:
        cidr_block_formatting (string): Cidr block formating
        instance_index (integer): Instance index
        subnet_suffix (string): subnet suffix

    Returns:
        string: Subnet cidr block
    """
    subnet_cidr_block = cidr_block_formatting.replace(
        "\\", "").format(instance_index, 0) + subnet_suffix
    return subnet_cidr_block


def get_vpc_gateway_ip(cidr_block_formatting):
    """Get vpc gateway IP

    Args:
        cidr_block_formatting (string): Cidr block formating

    Returns:
        string: Vpc gateway ip
    """
    vpc_gateway_ip = cidr_block_formatting.replace(
        "\\", "").format(0, 1)
    return vpc_gateway_ip


def get_subnet_cidr_suffix(ips_count, cidr_suffix_ips_number_mapping):
        """Get subnet cidr suffix

        Args:
            ips_count (integer): Ips count
            cidr_suffix_ips_number_mapping (dict): Cidr suffix ips number mapping

        Returns:
            string: subnet cidr suffix
        """
        cidr_suffix = "/28"
        if cidr_suffix_ips_number_mapping is not None:
            for item in cidr_suffix_ips_number_mapping:
                if item[0] > ips_count:
                    cidr_suffix = item[1]
                    break

        return cidr_suffix


def get_instance_eni_mapping(instance_type, eni_mapping):
    """Get instance elastic network interface mapping

    Args:
        instance_type (string): Instance type
        eni_mapping (dict): Elastic network interface mappings

    Returns:
        Tuple: Instance elastic network interface mapping
    """
    instance_eni_mapping = []

    if eni_mapping is not None:
        instance_eni_mapping = [
            item for item in eni_mapping if item[0] == instance_type]
    return instance_eni_mapping

