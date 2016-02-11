# Changelog

## %%version%% (unreleased)

### Other

* Add .gitchangelog.rc to help generating a changelog. [David Lonjon]


## 0.1.0 (2016-02-11)

### Other

* Rename the aws_proxies module to just proxies. [David Lonjon]

* Cleanup git ignore removing rules to remove bloating. [David Lonjon]

* Removing uneeded files for the package. [David Lonjon]

* Add python package ignore rules. [David Lonjon]

* Add a setup.py for packaging. [David Lonjon]

* Update the README with filler content. [David Lonjon]

* Rename README.md to README.rst. [David Lonjon]

* Add a MANIFEST.in file. [David Lonjon]

* Add a MIT License. [David Lonjon]

* Remove dependencies not needed. [David Lonjon]

* Move symaps_proxies into aws_proxies. [David Lonjon]

* Add a method to get all ip addresses for running proxies. [David Lonjon]

* Adding vpc and instances creation and deletion comfirmation as well printing progress. [David Lonjon]

* Fix code indentation. [David Lonjon]

* Rename variable for consistency and fix comments. [David Lonjon]

* Implement better logging level. [David Lonjon]

* Refactor code, consolidate and simpliy config for proxies creation. [David Lonjon]

* Remove the use of a local settings feature as this should become a package. [David Lonjon]

* Remove commented code. [David Lonjon]

* Make the setup_instances_groups_config method static and add comments. [David Lonjon]

* Create an instances module to simplify code structure and maintenance. [David Lonjon]

* Refactor and introduce a base resources class so other aws reeources can inherit from. [David Lonjon]

* Create a netwok interfaces module to simplify code structure and maintenance. [David Lonjon]

* Move some methods to utils modules and make some methods static methods. [David Lonjon]

* Remove witespaces. [David Lonjon]

* Standardize the way to delete route tables. [David Lonjon]

* Create a netwok acls module to simplify code structure and maintenance. [David Lonjon]

* Rename variable for consistency. [David Lonjon]

* Rename variable for consistency. [David Lonjon]

* Create a route tables module to simplify code structure and maintenance. [David Lonjon]

* Create a security groups module to simplify code structure and maintenance. [David Lonjon]

* Fix comments. [David Lonjon]

* Create a subnets module to simplify code structure and maintenance. [David Lonjon]

* Create an internet gateways module to simplify code structure and maintenance. [David Lonjon]

* Add a missing line return. [David Lonjon]

* Create a vpcs module to simplify code structure and maintenance. [David Lonjon]

* Add comments and rename variable for comprehension. [David Lonjon]

* Move the create_name_tag_for_resource and tag_with_name_with_suffix methods to the utils module. [David Lonjon]

* Add the missing utils module. [David Lonjon]

* Move the filter_resources method to the utils module. [David Lonjon]

* Move the merge_dicts and merge_config methods to the utils module. [David Lonjon]

* Move the query_yes_no method to utils module. [David Lonjon]

* Move create_suffix method to the utils module. [David Lonjon]

* Create a utils module and move the setting up of logger in that module. [David Lonjon]

* Simplify code. [David Lonjon]

* Move proxies class and rename it. [David Lonjon]

* Simplify exception catching. [David Lonjon]

* Simplify AWS interface initialisation, rename constant and cleanup local distribution settings. [David Lonjon]

* Remove unused import. [David Lonjon]

* Remove references to config folder and printing config into file not needed. [David Lonjon]

* Better structure code and add comments. [David Lonjon]

* Add a method to delete internet gateways and re-order the methods to delete vpcs resources to avoid errors. [David Lonjon]

* Add a method to delete internet gateways and re-order the methods to delete vpcs resources to avoid errors. [David Lonjon]

* Add a method to delete subnets. [David Lonjon]

* Add a method to delete security groups. [David Lonjon]

* Fix a typo. [David Lonjon]

* Create methods to delete network acls and route tables. [David Lonjon]

* Add methods to delete elastic network interfaces and terminate instances. [David Lonjon]

* Remove WIP method and optimise code for filtering enis while deleting public ips. [David Lonjon]

* Add a method to release public ips. [David Lonjon]

* Re-arrange code flow for better understanding. [David Lonjon]

* Fix pep8 code formatting. [David Lonjon]

* Automate more the creation of the user data script for running the instance. [David Lonjon]

* Add user data to instance creation. [David Lonjon]

* Add methods to assign public ips to enis and create instances. [David Lonjon]

* Fix a property name of the config object. [David Lonjon]

* Update the port to 8888 for one of the rule in the security group. [David Lonjon]

* Change some error logging to error raising. [David Lonjon]

* Rename varaibles for better understanding. [David Lonjon]

* Remove left over variable assignment used for testing. [David Lonjon]

* Fix PEP8 formatting errors. [David Lonjon]

* Implement better error catching. [David Lonjon]

* Fix info message formatting. [David Lonjon]

* Standardize the usage of single and double quotes. [David Lonjon]

* Add a feature to check image virtualization type against instance types. [David Lonjon]

* Fix the creation of network interfaces. [David Lonjon]

* Add feature to create network interfaces. [David Lonjon]

* Add a feature to create internet gateways routes. [David Lonjon]

* Allow to associate subnets to routes. [David Lonjon]

* Refactor the creation of the vpcs infrastructure. [David Lonjon]

* Update where the base tag name comes from in the config. [David Lonjon]

* Update vpcs config with subnets info from instance types config. [David Lonjon]

* Fix a uneeded nested list. [David Lonjon]

* Reformat code for better lisibility and remove unused variable statement. [David Lonjon]

* Remove redundant vpc id key in config. [David Lonjon]

* Add a feature to create network acls. [David Lonjon]

* Add back printing aws ec2 config of created infrastructure in json file. [David Lonjon]

* Fix a problem with unescape curly brackets in json. [David Lonjon]

* Rename variable to be consistant with naming convention. [David Lonjon]

* Add docblock to merge_config method. [David Lonjon]

* Fix a problem with getting internet gateway resource instead of id. [David Lonjon]

* Rename methods for better description. [David Lonjon]

* Heavily refactor create of vpcs resources. [David Lonjon]

* Improve code for filtering resources. [David Lonjon]

* Add feature to create route tables. [David Lonjon]

* Refactor code to bootstraps instance types config. [David Lonjon]

* Refactor code and make use of  a class global config. [David Lonjon]

* WIP - Create the framework to create instances. [David Lonjon]

* Fix PEP8 code formating. [David Lonjon]

* Add dictionary arguments to the constructor and add more properties for the class. [David Lonjon]

* Add AWS related config. [David Lonjon]

* Add a missing comma. [David Lonjon]

* Add a base setting to define eni mapping per instance type. [David Lonjon]

* Add a private method to create aws ec2 client. [David Lonjon]

* Remove unused import. [David Lonjon]

* Add feature to authorize ingress and egress security groups rules. [David Lonjon]

* Improve the way to add a name tag to ec2 resource. [David Lonjon]

* Add quotes for replaced strings in logger. [David Lonjon]

* Add creation of security groups. [David Lonjon]

* Implement writing  config as json to a file. [David Lonjon]

* Add a method to create aws ec2 subnets. [David Lonjon]

* Standardize dictionary keys name. [David Lonjon]

* Add method to merge config. [David Lonjon]

* Add a method to delete vpcs. [David Lonjon]

* Simplify the aws vpcs settings for testing. [David Lonjon]

* Refactor code to create vpc and to create internet gateways. [David Lonjon]

* Fix pep8 line width error. [David Lonjon]

* Refactor code for vpcs creation. [David Lonjon]

* Refactor AWS interfaces into a class. [David Lonjon]

* Implement creating of internet gateways. [David Lonjon]

* Change dictionary keys name to adjust with AWS keys naming convention. [David Lonjon]

* Improve comments. [David Lonjon]

* Add the creation of AWS VPCS and improve code. [David Lonjon]

* Make getting the AWS resource more generic. [David Lonjon]

* Add boto3 to requirements. [David Lonjon]

* Create an aws util using boto3 and setup a basic main program to test. [David Lonjon]

* Add jupyter rules to .gitignore. [David Lonjon]

* Add jupyter to the local requirements. [David Lonjon]

* Rename the symaps proxies module. [David Lonjon]

* Add a main.py file for the module. [David Lonjon]

* Add base and local dist settings files. [David Lonjon]

* Add local.py settings to .gitignore. [David Lonjon]

* Remove .gitignore rule related to ansible. [David Lonjon]

* Add a settings directory to the symaps-proxies module. [David Lonjon]

* Add a test directory for the symaps-proxies module. [David Lonjon]

* Add pytest as a local requirement. [David Lonjon]

* Add the symaps-proxies module. [David Lonjon]

* Add a docs directory for project structure. [David Lonjon]

* Add a bin directory for project structure. [David Lonjon]

* Remove bin from .gitignore. [David Lonjon]

* Add requirements files. [David Lonjon]

* Add .pep8. [David Lonjon]

* Add .gitignore. [David Lonjon]

* Add a README file. [David Lonjon]


