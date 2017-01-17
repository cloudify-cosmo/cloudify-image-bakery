import os
import base64
import subprocess
from ConfigParser import ConfigParser

from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify.state import ctx_parameters as inputs

AZURE_PLUGIN_CONF = '/root/azure_config.json'


def get_auth_header(username, password):
    header = None

    if username and password:
        credentials = '{0}:{1}'.format(username, password)
        header = {
            'Authorization':
                'Basic' + ' ' + base64.urlsafe_b64encode(credentials)}

    return header


def create_azure_config(manager_config_path, manager_config):
    config = ConfigParser()

    config.add_section('Credentials')
    config.set('Credentials', 'subscription_id',
               manager_config['subscription_id'])
    config.set('Credentials', 'tenant_id',
               manager_config['tenant_id'])
    config.set('Credentials', 'client_id',
               manager_config['client_id'])
    config.set('Credentials', 'client_secret',
               manager_config['client_secret'])

    config.add_section('Azure')
    config.set('Azure', 'location',
               manager_config['location'])

    ctx.logger.info('Saving azure config: {0}'.format(manager_config_path))
    with open(manager_config_path, 'w') as temp_config_file:
        config.write(temp_config_file)


def update_context(agent_pk_path,
                   agent_user):

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

    ctx.logger.info('Updating context')
    c.manager.update_context(name, context)


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


def main():
    private_key_path, public_key_path = create_agents_keypair(
            path='~/.ssh',
            kp_name=inputs['agents_keypair_name'],
    )

    with open(public_key_path) as public_key_handle:
        public_key = public_key_handle.read()
        ctx.instance.runtime_properties['agents_public_key'] = public_key

    manager_config= dict(
            subscription_id=inputs["subscription_id"],
            tenant_id=inputs["tenant_id"],
            client_id=inputs["client_id"],
            client_secret=inputs["client_secret"],
            location=inputs["location"]
    )

    create_azure_config(
            manager_config_path=AZURE_PLUGIN_CONF,
            manager_config=manager_config
    )

    allow_manager_ports()

    update_context(
            agent_pk_path=private_key_path,
            agent_user=inputs['agents_user']
    )


if __name__ == '__main__':
    main()
