import base64
import os
import urllib2
from ConfigParser import ConfigParser

from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify.state import ctx_parameters as inputs


BOTO_CONF = os.path.expanduser('~/.boto')


def get_auth_header(username, password):
    header = None

    if username and password:
        credentials = '{0}:{1}'.format(username, password)
        header = {
            'Authorization':
            'Basic' + ' ' + base64.urlsafe_b64encode(credentials)}

    return header


def get_manager_instance(conn):
    url = 'http://169.254.169.254/latest/meta-data/instance-id'
    instance_id = urllib2.urlopen(url).read().split()[0]

    return conn.get_only_instances(instance_ids=[instance_id])[0]


def get_region():
    url = 'http://169.254.169.254/latest/meta-data/placement/availability-zone'
    return urllib2.urlopen(url).read()[:-1]


def create_boto_config(path, aws_access_key_id, aws_secret_access_key, region):
    config = ConfigParser()

    config.add_section('Credentials')
    config.set('Credentials',
               'aws_access_key_id',
               aws_access_key_id)
    config.set('Credentials',
               'aws_secret_access_key',
               aws_secret_access_key)

    config.add_section('Boto')
    config.set('Boto', 'ec2_region_name', region)

    ctx.logger.info('Saving boto config: {0}'.format(path))
    with open(path, 'w') as fh:
        config.write(fh)


def create_agents_security_group(conn,
                                 agents_sg_name,
                                 manager_security_group,
                                 vpc_id):
    ctx.logger.info('Creating agent security group: {0}'
                    .format(agents_sg_name))

    agents_sg_desc = 'Security group for Cloudify agent VMs'
    agents_sg = conn.create_security_group(
        agents_sg_name,
        agents_sg_desc,
        vpc_id=vpc_id,
    )

    # authorize from manager to agents
    add_tcp_allows_to_security_group(
        port_list=[22, 5985],
        security_group=agents_sg,
        from_group=manager_security_group,
    )

    return agents_sg


def configure_manager_security_group(manager_security_group,
                                     inbound_ports,
                                     agents_security_group):
    # authorize from agent to manager
    add_tcp_allows_to_security_group(
        port_list=inbound_ports,
        security_group=manager_security_group,
        from_group=agents_security_group,
    )


def add_tcp_allows_to_security_group(port_list,
                                     security_group,
                                     from_group):
    for port in port_list:
        security_group.authorize('tcp', port, port, src_group=from_group)


def create_keypair(conn, path, kp_name):
    ctx.logger.info('Creating keypair: {0}'.format(kp_name))
    kp = conn.create_key_pair(kp_name)

    pk_path = os.path.join(path, kp.name + '.pem')
    ctx.logger.info('Saving keypair to: {0}'.format(pk_path))
    if not kp.save(path):
        raise RuntimeError('Failed saving keypair')

    return kp.name, pk_path


def update_context(agent_sg_id, agent_kp_id, agent_pk_path, agent_user):
    security_enabled = os.path.exists(
        '/root/.cloudify_image_security_enabled'
    )
    if security_enabled:
        auth_header = get_auth_header('cloudify', 'cloudify')
        cert_path = '/root/cloudify/server.crt'
        c = CloudifyClient(
            headers=auth_header,
            cert=cert_path,
            trust_all=False,
            port=443,
            protocol='https',
        )
    else:
        c = CloudifyClient()

    name = c.manager.get_context()['name']
    context = c.manager.get_context()['context']
    context['cloudify']['cloudify_agent']['agent_key_path'] = agent_pk_path
    context['cloudify']['cloudify_agent']['user'] = agent_user

    resources = {
        'agents_security_group': {
            'external_resource': False,
            'id': agent_sg_id
        },
        'agents_keypair': {
            'external_resource': False,
            'id': agent_kp_id
        }
    }
    context['resources'] = resources

    ctx.logger.info('Updating context')
    c.manager.update_context(name, context)


def main():
    create_boto_config(
        path=BOTO_CONF,
        aws_access_key_id=inputs['aws_access_key'],
        aws_secret_access_key=inputs['aws_secret_key'],
        region=get_region(),
    )

    # This import must occur here as this is when the boto config file is
    # accessed to get credentials
    import boto.ec2
    conn = boto.ec2.EC2Connection()

    manager_instance = get_manager_instance(conn=conn)
    manager_security_groups = conn.get_all_security_groups(group_ids=[
        group.id for group in manager_instance.groups
        # I believe this is only security groups, but to be safe we will
        # filter for only security group IDs
        if group.id.startswith('sg-')
    ])

    # The first listed security group will be the one we treat as primary
    manager_security_group = manager_security_groups[0]

    manager_vpc_id = manager_instance.vpc_id

    agents_sg = create_agents_security_group(
        conn=conn,
        agents_sg_name=inputs['agents_security_group_name'],
        manager_security_group=manager_security_group,
        vpc_id=manager_vpc_id,
    )

    configure_manager_security_group(
        manager_security_group=manager_security_group,
        inbound_ports=[int(port) for port in
                       inputs['agents_to_manager_inbound_ports'].split(',')],
        agents_security_group=agents_sg,
    )

    akp_id, apk_path = create_keypair(conn=conn,
                                      path='~/.ssh/',
                                      kp_name=inputs['agents_keypair_name'])

    update_context(agent_sg_id=agents_sg.id,
                   agent_kp_id=akp_id,
                   agent_pk_path=apk_path,
                   agent_user=inputs['agents_user'])

if __name__ == '__main__':
    main()
