import os
import sys
import urllib2
import subprocess
from ConfigParser import ConfigParser

from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify.state import ctx_parameters as inputs


BOTO_CONF = os.path.expanduser('~/.boto')


def get_manager_sg():
    url = 'http://169.254.169.254/latest/meta-data/security-groups'
    return urllib2.urlopen(url).read().split()[0]


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


def create_agent_sg(sg_name):
    import boto.ec2

    ctx.logger.info('Creating agent security group: {0}'
                    .format(sg_name))

    conn = boto.ec2.EC2Connection()
    sg_desc = 'Security group for Cloudify agent VMs'
    sg = conn.create_security_group(sg_name, sg_desc)
    manager_sg = conn.get_all_security_groups(groupnames=get_manager_sg())[0]
    ctx.logger.info('Manager group name: {0}'.format(manager_sg))

    # authorize from manager to agents
    sg.authorize('tcp', 22, 22, src_group=manager_sg)
    sg.authorize('tcp', 5985, 5985, src_group=manager_sg)

    # authorize from agent to manager
    manager_sg.authorize(src_group=sg)

    return sg.id


def install_boto():
    ctx.logger.info('Installing boto')
    if not hasattr(sys, 'real_prefix'):
        raise RuntimeError('Not running inside virtualenv directory')

    pip_fpath = os.path.join(sys.prefix, 'bin', 'pip')
    cmd = [pip_fpath, 'install', 'boto==2.34.0']
    exit_code = subprocess.call(cmd)

    ctx.logger.info('Install exit code: {0}'.format(exit_code))
    if exit_code != 0:
        raise RuntimeError('Boto install ended with non zero exit code')


def create_keypair(path, kp_name):
    import boto.ec2

    ctx.logger.info('Creating keypair: {0}'.format(kp_name))
    conn = boto.ec2.EC2Connection()
    kp = conn.create_key_pair(kp_name)

    pk_path = os.path.join(path, kp.name + '.pem')
    ctx.logger.info('Saving keypair to: {0}'.format(pk_path))
    if not kp.save(path):
        raise RuntimeError('Failed saving keypair')

    return kp.name, pk_path


def update_context(agent_sg_id, agent_kp_id, agent_pk_path, agent_user):
    c = CloudifyClient()
    name = c.manager.get_context()['name']
    context = c.manager.get_context()['context']
    context['cloudify']['cloudify_agent']['agent_key_path'] = agent_pk_path
    context['cloudify']['cloudify_agent']['user'] = agent_user

    resources = {
        'agents_security_group':
            {
                'external_resource': False,
                'id': agent_sg_id
            },
        'agents_keypair':
            {
                'external_resource': False,
                'id': agent_kp_id
            }
    }
    context['resources'] = resources

    ctx.logger.info('Updating context')
    c.manager.update_context(name, context)


def main():
    install_boto()

    create_boto_config(path=BOTO_CONF,
                       aws_access_key_id=inputs['aws_access_key_id'],
                       aws_secret_access_key=inputs['aws_secret_access_key'],
                       region=get_region())

    sg_id = create_agent_sg(sg_name=inputs['agent_security_group_name'])
    
    akp_id, apk_path = create_keypair(path='~/.ssh/', 
                                      kp_name=inputs['agent_keypair_name'])

    update_context(agent_sg_id=sg_id,
                   agent_kp_id=akp_id,
                   agent_pk_path=apk_path,
                   agent_user=inputs['agents_user'])

if __name__ == '__main__':
    main()
