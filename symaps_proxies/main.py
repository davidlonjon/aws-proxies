# -*- coding: utf-8 -*-

import lib.common.aws_utils as aws
import sys

try:
    session = aws.get_aws_session('david_dev')
except Exception:
    print "Could not open AWS session"
    sys.exit()

try:
    ec2 = aws.get_aws_resource(session, 'ec2')
except Exception:
    print "Could not access AWS EC2 resource"
    sys.exit()

for i in ec2.instances.all():
    print(i)
