import base64
from copy import copy
import json
import os
import subprocess

from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify.state import ctx_parameters as inputs
from cloudify.exceptions import NonRecoverableError
from neutronclient.v2_0 import client as neutronclient
from novaclient.v2 import client as novaclient

OPENSTACK_PLUGIN_CONF = '/root/openstack_config.json'
AGENTS_KEY_PATH = '/root/.ssh/agent_key.pem'


def create_openstack_config(username,
                            password,
                            tenant_name,
                            region,
                            auth_url):
    config = {
        'username': username,
        'password': password,
        'tenant_name': tenant_name,
        'region': region,
        'auth_url': auth_url,
    }
    conf_dir = os.path.dirname(OPENSTACK_PLUGIN_CONF)
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    with open(OPENSTACK_PLUGIN_CONF, 'w') as conf_handle:
        json.dump(config, conf_handle)


def get_auth_header(username, password):
    header = None

    if username and password:
        credentials = '{0}:{1}'.format(username, password)
        header = {
            'Authorization':
            'Basic' + ' ' + base64.urlsafe_b64encode(credentials)}

    return header


def build_resources_context(server,
                            agents_keypair_name,
                            agents_secgroup_name,
                            nova_client,
                            neutron_client):
    resources = {}

    resources['agents_keypair'] = {
        'external_resource': False,
        'id': agents_keypair_name,
        'name': agents_keypair_name,
        'type': 'keypair',
    }

    resources['agents_security_group'] = {
        'external_resource': False,
        'id': agents_secgroup_name,
        'name': agents_secgroup_name,
        'type': 'security_group',
    }

    floating_ip_address = None
    for address in server.addresses.values():
        for listing in address:
            if listing['OS-EXT-IPS:type'] == 'floating':
                floating_ip_address = listing['addr']
                floating_ip_id = nova_client.floating_ips.find(
                    ip=floating_ip_address,
                ).id
                break
    if floating_ip_address is not None:
        resources['floating_ip'] = {
            'external_resource': True,
            'id': floating_ip_id,
            'ip': floating_ip_address,
            'type': 'floatingip',
        }

    int_network_name = server.networks.keys()[0]
    int_network_id = nova_client.networks.find(human_id=int_network_name).id
    resources['int_network'] = {
        'external_resource': True,
        'id': int_network_id,
        'name': int_network_name,
        'type': 'network',
    }

    resources['management_keypair'] = {
        'external_resource': True,
        'id': server.key_name,
        'name': server.key_name,
        'type': 'keypair',
    }

    manager_sec_group_name = server.security_groups[0]['name']
    manager_sec_group_id = nova_client.security_groups.find(
        name=manager_sec_group_name,
    ).id
    resources['management_security_group'] = {
        'external_resource': True,
        'id': manager_sec_group_id,
        'name': manager_sec_group_name,
        'type': 'security_group',
    }

    neutron_nets = {
        net['id']: net
        for net in neutron_client.list_networks()['networks']
    }
    int_network = neutron_nets[int_network_id]

    neutron_subnets = {
        subnet['id']: subnet
        for subnet in neutron_client.list_subnets()['subnets']
    }

    neutron_routers = {
        router['id']: router
        for router in neutron_client.list_routers()['routers']
    }
    neutron_router_interfaces = [
        port for port in neutron_client.list_ports()['ports']
        if port['device_owner'] == 'network:router_interface'
    ]
    router_interface = None
    for iface in neutron_router_interfaces:
        if iface['network_id'] == int_network_id:
            router_interface = iface
            break
    router = neutron_routers[router_interface['device_id']]

    resources['router'] = {
        'external_resource': True,
        'id': router['id'],
        'name': router['name'],
        'type': 'router',
    }

    # There can be multiple subnets, so in future this should be improved to
    # do a check that the server IP is in the subnet's IP range as there does
    # not appear to be a more sensible way
    int_subnet = neutron_subnets[int_network['subnets'][0]]
    resources['subnet'] = {
        'external_resource': True,
        'id': int_subnet['id'],
        'name': int_subnet['name'],
        'type': 'subnet',
    }

    router_ext_net = router['external_gateway_info']['network_id']
    ext_network = neutron_nets[router_ext_net]
    resources['ext_network'] = {
        'external_resource': True,
        'id': ext_network['id'],
        'name': ext_network['name'],
        'type': 'network',
    }

    return resources


def get_subnet_cidr(subnet_id, neutron_client):
    subnets = {
        subnet['id']: subnet
        for subnet in neutron_client.list_subnets()['subnets']
    }
    return subnets[subnet_id]['cidr']


def create_agents_keys(nova_client, agents_keypair_name):
    # TODO: Catch error here and make unrecoverable, because we won't have the
    # private key
    keypair = nova_client.keypairs.create(name=agents_keypair_name)
    with open(AGENTS_KEY_PATH, 'w') as priv_key_handle:
        priv_key_handle.write(keypair.private_key)


def create_agents_security_group(nova_client,
                                 agents_secgroup_name,
                                 manager_cidr):
    security_group = nova_client.security_groups.create(
        name=agents_secgroup_name,
        description="Security group for Cloudify agent VMs",
    )

    add_tcp_allows_to_security_group(
        nova_client=nova_client,
        port_list=[22, 5985],
        cidr=manager_cidr,
        security_group_id=security_group.id,
    )


def add_tcp_allows_to_security_group(nova_client,
                                     port_list,
                                     cidr,
                                     security_group_id):
    base_rule_details = {
        'ip_protocol': 'tcp',
        'cidr': cidr,
        'parent_group_id': security_group_id,
    }

    required_rules = [
        {
            'from_port': port,
            'to_port': port,
        }
        for port in port_list
    ]

    for rule in required_rules:
        rule_details = copy(base_rule_details)
        rule_details.update(rule)
        try:
            nova_client.security_group_rules.create(**rule_details)
        # TODO: This is probably a BadRequest, make it more specific
        except Exception as err:
            if 'This rule already exists in group' in str(err):
                # If the rule already exists that is not a problem
                pass
            else:
                raise err


def update_context(server,
                   resources_context,
                   agents_user):
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
    context['cloudify']['cloudify_agent']['agent_key_path'] = AGENTS_KEY_PATH
    context['cloudify']['cloudify_agent']['user'] = agents_user
    context['resources'] = resources_context
    ctx.logger.info('Updating context')
    c.manager.update_context(name, context)


def get_server_by_mac(nova_client, mac_address):
    """
        The only information we can get from the server itself that is unique
        and visible through the openstack API is the MAC address.
    """
    servers = nova_client.servers.list()

    for server in servers:
        for address in server.addresses.values():
            for listing in address:
                if listing['OS-EXT-IPS-MAC:mac_addr'] == mac_address:
                    return server
    # If we got this far, we found no relevant server
    return None


def get_mac_address():
    # First, try to find the device the default route is on, which we can
    # reasonably expect to be a real device
    # expected format is:
    # <route> via <router> dev <device>
    # or
    # <route> dev <device> proto kernel scope link src <ip>
    # for both, looking for the next token after 'dev' works.
    # This method was used as it is simpler than processing all interfaces
    routes = subprocess.check_output(['ip', 'ro', 'sho']).splitlines()
    device = None
    for route in routes:
        if 'default' in route:
            route = route.split()
            if 'dev' in route:
                device = route[route.index('dev') + 1]
                break

    # If there was no device with a default route, we'll get the first device
    # that isn't the loopback
    if device is None:
        for route in routes:
            route = route.split()
            if 'dev' in route:
                device = route[route.index('dev') + 1]
                if device == 'lo':
                    # The loopback is undesirable
                    device = None
                else:
                    break

    if device is None:
        raise NonRecoverableError(
            'Could not retrieve a non loopback network interface for details'
        )

    # Now that we have a device, we can get the details of that device
    device_details = subprocess.check_output(['ip', 'a', 's', device])
    device_details = device_details.split()
    mac_address = device_details[device_details.index('link/ether') + 1]

    return mac_address


def configure_manager_security_group(nova_client,
                                     inbound_ports,
                                     management_subnet_cidr,
                                     management_security_group_id):
    add_tcp_allows_to_security_group(
        nova_client=nova_client,
        port_list=inbound_ports,
        cidr=management_subnet_cidr,
        security_group_id=management_security_group_id,
    )


def main():
    nova_client = novaclient.Client(
        username=inputs['openstack_username'],
        api_key=inputs['openstack_password'],
        auth_url=inputs['openstack_auth_url'],
        project_id=inputs['openstack_tenant_name'],
        region=inputs['openstack_region'],
    )
    neutron_client = neutronclient.Client(
        username=inputs['openstack_username'],
        password=inputs['openstack_password'],
        auth_url=inputs['openstack_auth_url'],
        tenant_name=inputs['openstack_tenant_name'],
        region=inputs['openstack_region'],
    )

    create_openstack_config(
        username=inputs['openstack_username'],
        password=inputs['openstack_password'],
        tenant_name=inputs['openstack_tenant_name'],
        region=inputs['openstack_region'],
        auth_url=inputs['openstack_auth_url'],
    )

    server = get_server_by_mac(
        mac_address=get_mac_address(),
        nova_client=nova_client,
    )

    resources_context = build_resources_context(
        server=server,
        agents_keypair_name=inputs['agents_keypair_name'],
        agents_secgroup_name=inputs['agents_security_group_name'],
        nova_client=nova_client,
        neutron_client=neutron_client,
    )

    create_agents_keys(
        nova_client=nova_client,
        agents_keypair_name=inputs['agents_keypair_name'],
    )

    manager_cidr = get_subnet_cidr(
        subnet_id=resources_context['subnet']['id'],
        neutron_client=neutron_client,
    )

    create_agents_security_group(
        nova_client=nova_client,
        agents_secgroup_name=inputs['agents_security_group_name'],
        manager_cidr=manager_cidr,
    )

    management_security_group = resources_context['management_security_group']
    configure_manager_security_group(
        nova_client=nova_client,
        inbound_ports=[int(port) for port in
                       inputs['agents_to_manager_inbound_ports'].split(',')],
        management_subnet_cidr=manager_cidr,
        management_security_group_id=management_security_group['id'],
    )

    update_context(
        server=server,
        resources_context=resources_context,
        agents_user=inputs['agents_user'],
    )


if __name__ == '__main__':
    main()
