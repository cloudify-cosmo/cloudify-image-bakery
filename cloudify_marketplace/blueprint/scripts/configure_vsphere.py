import os
import subprocess

import yaml
from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify.state import ctx_parameters as inputs


def create_agents_keypair(path, kp_name):
    ctx.logger.info('Creating keypair: {0}'.format(kp_name))

    path = os.path.expanduser(path)
    # Ensure ssh path exists
    if not os.path.exists(path):
        os.mkdir(path)

    private_key_path = os.path.join(path, kp_name + '.pem')
    public_key_path = os.path.join(path, kp_name + '.pem.pub')
    ctx.logger.info('Generating agents keypair: {0}'.format(private_key_path))

    subprocess.call([
        'sudo',
        'ssh-keygen',
        '-f',
        private_key_path,
        '-N',
        '',
        '-b',
        '4096',
    ])

    return private_key_path, public_key_path


def create_vsphere_config(vsphere_username,
                          vsphere_password,
                          vsphere_host,
                          vsphere_port,
                          vsphere_datacenter_name,
                          vsphere_resource_pool_name,
                          vsphere_auto_placement,
                          path='/root/connection_config.yaml'):
    with open(path, 'w') as conf_handle:
        conf_handle.write(yaml.dump({
            "username": vsphere_username,
            "password": vsphere_password,
            "host": vsphere_host,
            "port": vsphere_port,
            "datacenter_name": vsphere_datacenter_name,
            "resource_pool_name": vsphere_resource_pool_name,
            "auto_placement": vsphere_auto_placement,
        }))


def allow_manager_ports():
    for port in [5672, 8101, 53229]:
        allow_port_through_firewall(port)


def allow_port_through_firewall(port, proto='tcp'):
    subprocess.call([
        'sudo',
        'firewall-cmd',
        '--zone=public',
        '--permanent',
        '--add-port={port}/{proto}'.format(
            port=port,
            proto=proto
        )
    ])
    subprocess.call([
        'sudo',
        'firewall-cmd',
        '--reload',
    ])


def update_context(agent_pk_path, agent_user):
    c = CloudifyClient()
    name = c.manager.get_context()['name']
    context = c.manager.get_context()['context']
    context['cloudify']['cloudify_agent']['agent_key_path'] = agent_pk_path
    context['cloudify']['cloudify_agent']['user'] = agent_user

    ctx.logger.info('Updating context')
    c.manager.update_context(name, context)


def main():
    private_key_path, public_key_path = create_agents_keypair(
        path='~/.ssh',
        kp_name=inputs['agents_keypair_name'],
    )

    with open(public_key_path) as public_key_handle:
        public_key = public_key_handle.read()
        ctx.instance.runtime_properties['agents_public_key'] = public_key

    create_vsphere_config(
        vsphere_username=inputs["vsphere_username"],
        vsphere_password=inputs["vsphere_password"],
        vsphere_host=inputs["vsphere_host"],
        vsphere_port=inputs["vsphere_port"],
        vsphere_datacenter_name=inputs["vsphere_datacenter_name"],
        vsphere_resource_pool_name=inputs["vsphere_resource_pool_name"],
        vsphere_auto_placement=inputs["vsphere_auto_placement"],
    )

    allow_manager_ports()

    update_context(
        agent_pk_path=private_key_path,
        agent_user=inputs['agents_user'],
    )

if __name__ == '__main__':
    main()
