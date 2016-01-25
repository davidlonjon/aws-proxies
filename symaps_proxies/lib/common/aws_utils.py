# -*- coding: utf-8 -*-
import boto3


def get_aws_session(profile):
    """Get AWS Session

    Args:
        profile (string): AWS credential profile

    Returns:
        object: AWS session object
    """
    session = boto3.Session(profile_name=profile)
    return session


def get_ec2_resource(session):
    """Get EC2 Resource

    Args:
        session (object): AWS session

    Returns:
        object: EC2 resource
    """
    ec2 = session.resource('ec2')
    return ec2
