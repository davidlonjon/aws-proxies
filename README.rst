AWS Proxies
===========

This allows to create AWS instances with multiple public ips to create
proxies servers.

This is still under heavy development. Use at own risk.

Installation
------------

Using Pip:

::

    $ pip install -e git+git@github.com:davidlonjon/aws proxies.git@develop#egg=aws_proxies

If using a requirement file, add the following in the file:

``-e git+git@github.com:davidlonjon/aws-proxies.git@develop#egg=aws_proxies``

Usage
-----

::

    from aws_proxies.proxies import Proxies

    # This is the first required step
    proxies = Proxies(profile='put_your_aws_profile')
    # or if want to see more output use:
    # proxies = Proxies(profile='put_your_aws_profile', log_level=20)


    # To create the proxies
    # Note that the tinyproxy image name need to exists in your owned AMI
    # Tinyproxy needs to run on port 8888
    # This will create 1 micro instance bound to 4 public IP addresses in the
    # 15.0.0.0/16 VPC. The VPC, subnets, internet gateways will all be created automatically.

    proxies_config = {
        "available_ips": 4,
        "instances_config": [
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
                        ]
                    }
                ]
            }
        ]
    }

    proxies.create(proxies_config=proxies_config, ask_confirm=True, silent=False)
    # Without confirmation and completely silent
    proxies.create(proxies_config=proxies_config, ask_confirm=False, silent=True)


    # To get the public and private ips of the proxies
    ips = proxies.instances.get_running_proxies_ips(silent=False)
    # ips will be a list of tuples such as [(public_ip, private_ip), (public_ip, private_ip), ...]

    # To terminate the proxies and the VPC infrastructure
    proxies.delete(ask_confirm=False, silent=True)

Contributing
------------

1. Fork it!
2. Create your feature branch: ``git checkout -b my-new-feature``
3. Commit your changes: ``git commit -am 'Add some feature'``
4. Push to the branch: ``git push origin my-new-feature``
5. Submit a pull request :D
