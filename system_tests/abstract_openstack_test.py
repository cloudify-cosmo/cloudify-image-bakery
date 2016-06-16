########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
import os
import string

from cloudify.workflows import local
from cloudify_cli import constants as cli_constants
from novaclient.v2 import client as novaclient

from .abstract_packer_test import AbstractPackerTest


class AbstractOpenstackTest(AbstractPackerTest):
    packer_build_only = 'openstack'
    hello_world_blueprint_file = 'blueprint.yaml'

    def setUp(self):
        super(AbstractOpenstackTest, self).setUp()

        safe_chars = set("_- " + string.digits + string.ascii_letters)
        # From nova/compute/api.py
        self.assertTrue(
            set(self.agents_keypair) <= safe_chars,
            '"Unsafe" chars used in keypair name.')

        self.config_inputs.update({
            'user_ssh_key': self.conf['openstack_ssh_keypair_name'],
            'agents_security_group_name': self.agents_secgroup,
            'agents_keypair_name': self.agents_keypair,
            'agents_user': self.conf.get('openstack_agents_user', 'ubuntu'),
            'openstack_username': self.conf['keystone_username'],
            'openstack_password': self.conf['keystone_password'],
            'openstack_auth_url': self.conf['keystone_url'],
            'openstack_tenant_name': self.conf['keystone_tenant_name'],
            'openstack_region': self.conf['region'],
            })

        self.hello_world_inputs = {
            'agent_user': 'ubuntu',
            'image': self.env.ubuntu_trusty_image_name,
            'flavor': self.env.flavor_name
        }

    def _get_conn(self):
        return novaclient.Client(
            username=self.env.cloudify_config['keystone_username'],
            api_key=self.env.cloudify_config['keystone_password'],
            auth_url=self.env.cloudify_config['keystone_url'],
            project_id=self.env.cloudify_config['keystone_tenant_name'],
            region=self.env.cloudify_config['region'],
        )

    def _find_image(self):
        conn = self._get_conn()

        image_id = None

        # Tenant ID does not appear to be populated until another action has
        # been taken, so we will make a call to cause it to be populated.
        # We use floating IPs as this shouldn't be a huge amount of data.
        # We could try making a call that will return nothing, but those may
        # raise exceptions so we will trust that list should not do so.
        conn.floating_ips.list()
        my_tenant_id = conn.client.tenant_id

        images = conn.images.list()
        self.logger.info('Images from platform: %s' % images)
        images = [image.to_dict() for image in images]
        self.logger.info('Tenant ID: %s' % my_tenant_id)
        for image in images:
            self.logger.info(image['metadata'])
        # Get just the images belonging to this tenant
        images = [
            image for image in images
            if 'owner_id' in image['metadata'].keys() and
            # 'and' on previous line due to PEP8
            image['metadata']['owner_id'] == my_tenant_id
        ]
        self.logger.info('All images: %s' % images)
        self.logger.info('Searching by prefix: %s' % self.name_prefix)
        # Filter for the prefix
        for image in images:
            self.logger.info('Checking %s...' % image['name'])
            if image['name'].startswith(self.name_prefix):
                self.logger.info('Correct image, with ID: %s' % image['id'])
                image_id = image['id']
                break

        return image_id

    def deploy_image(self):
        blueprint_path = self.copy_blueprint('openstack-start-vm')
        self.openstack_blueprint_yaml = os.path.join(
            blueprint_path,
            'blueprint.yaml'
        )
        self.prefix = 'packer-system-test-{0}'.format(self.test_id)

        self.openstack_inputs = {
            'prefix': self.prefix,
            'external_network': self.env.cloudify_config[
                'openstack_external_network_name'],
            'os_username': self.env.cloudify_config['keystone_username'],
            'os_password': self.env.cloudify_config['keystone_password'],
            'os_tenant_name': self.env.cloudify_config[
                'keystone_tenant_name'],
            'os_region': self.env.cloudify_config['region'],
            'os_auth_url': self.env.cloudify_config['keystone_url'],
            'image_id': self.images['openstack'],
            'flavor': self.env.cloudify_config[
                'openstack_marketplace_flavor'],
            'key_pair_path': '{0}/{1}-keypair.pem'.format(self.workdir,
                                                          self.prefix)
        }

        self.logger.info('initialize local env for running the '
                         'blueprint that starts a vm')
        self.manager_env = local.init_env(
            self.openstack_blueprint_yaml,
            inputs=self.openstack_inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES
        )

        self.logger.info('starting vm to serve as the management vm')
        self.manager_env.execute('install',
                                 task_retries=10,
                                 task_retry_interval=30)

        outputs = self.manager_env.outputs()
        self.manager_public_ip = outputs[
            'simple_vm_public_ip_address'
        ]

        self.addCleanup(self._undeploy_image)

    def _delete_image(self, image_id):
        conn = self._get_conn()
        image = conn.images.find(id=image_id)
        image.delete()

    def _delete_agents_keypair(self):
        conn = self._get_conn()
        keypair = conn.keypairs.find(name=self.agents_keypair)
        keypair.delete()

    def _delete_agents_secgroup(self):
        conn = self._get_conn()
        secgroup = conn.security_groups.find(
            name=self.agents_secgroup
        )
        secgroup.delete()
