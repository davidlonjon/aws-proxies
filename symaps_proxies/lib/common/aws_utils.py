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


def get_aws_resource(session, resource):
    """Get AWS resource

    Args:
        session (object): AWS session
        resource (string): AWS resource

    Returns:
        object: EC2 resource
    """
    resource = session.resource(resource)
    return resource
