# ec2 instance start-up script
#
# You must run this script with root privileges (>sudo python glue_script.py)
# before running this script make sure you have set the aws credentials in the
# following files:
# 	/etc/boto.cfg - for all users on this machine
# 	~/.boto - for current user
#
# The config file should look like this:
# 	[Credentials]
# 	aws_access_key_id = <your_access_key>
# 	aws_secret_access_key = <your_secret_key>
#

import boto.ec2
import boto.route53
import boto.utils
import time
import os


def init_connection():
    # connect to the ec2 user account
    conn = boto.ec2.connect_to_region("us-west-2")
    return conn


def add_name_tag(conn):

    # get the local instance_id and userdata
    metadata = boto.utils.get_instance_metadata()
    instance_id = metadata['instance-id']
    userdata = boto.utils.get_instance_userdata()

    instances = conn.get_only_instances()
    for i in instances:
        if i.id == instance_id:
            instance = i

    print "Instance id: ", instance.id
    print "Instance type: ", instance.instance_type
    print "Instance placement: ", instance.placement
    print "Instance status: ", instance.update()

    instance_state = instance.update()
    while instance_state == 'pending':
        time.sleep(5)
        instance_state = instance.update()

    if instance_state == 'running':

        print "Instance userData: ", userdata
        print "Creating tag name '%s' for instance id %s ..." % \
            (userdata, instance.id)
        # add the name tag to the instance
        conn.create_tags([instance.id], {"Name": userdata})
        print "Tag name added."

    else:
        print "Instance status: ", instance_state
        return None

    return userdata


def set_hostname(name_tag):

    # delete /etc/hostname file content
    hostname_file = open('/etc/hostname', 'r+')
    hostname_file.seek(0)
    hostname_file.truncate()
    hostname_file.seek(0)

    # write the new hostname
    hostname_file.write(name_tag)
    hostname_file.write('\n')
    hostname_file.close()

    hostname = "sudo hostname -b " + name_tag
    os.system(hostname)


def add_route53_rrecord(name_tag):

    conn = boto.route53.connect_to_region('us-west-2')
    zone_name = 'example1.com.'
    zone = conn.get_zone(zone_name)

    if zone is None:
        zone = conn.create_zone(zone_name)
    else:
        # create an A resource record
        metadata = boto.utils.get_instance_metadata()
        public_ip = metadata['public-ipv4']
        name = name_tag + "." + zone_name
        zone.add_record('A', name, public_ip)


def main():

    connection = init_connection()
    name_tag = add_name_tag(connection)
    set_hostname(name_tag)
    add_route53_rrecord(name_tag)


if __name__ == "__main__":
    main()
