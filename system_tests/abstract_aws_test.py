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

from cloudify.workflows import local
from cloudify_cli import constants as cli_constants
import boto.ec2

from .abstract_packer_test import AbstractPackerTest


class AbstractAwsTest(AbstractPackerTest):
    packer_build_only = 'aws'
    hello_world_blueprint_file = 'ec2-vpc-blueprint.yaml'

    def setUp(self):
        super(AbstractAwsTest, self).setUp()

        self.config_inputs.update({
            'user_ssh_key': self.conf['aws_ssh_keypair_name'],
            'agents_user': self.conf.get('aws_agents_user', 'ubuntu'),
            'aws_access_key': self.conf['aws_access_key'],
            'aws_secret_key': self.conf['aws_secret_key'],
            })

        self.hello_world_inputs = {
            'agent_user': 'ubuntu',
            'image_id': self.conf['aws_trusty_image_id'],
            'vpc_id': self.conf['aws_vpc_id'],
            'vpc_subnet_id': self.conf['aws_subnet_id'],
        }

    def _get_conn(self):
        return boto.ec2.EC2Connection(
            aws_access_key_id=self.env.cloudify_config[
                'aws_access_key'],
            aws_secret_access_key=self.env.cloudify_config[
                'aws_secret_key'],
        )

    def deploy_image(self):
        blueprint_path = self.copy_blueprint('aws-vpc-start-vm')
        self.aws_blueprint_yaml = os.path.join(
            blueprint_path,
            'blueprint.yaml'
        )

        self.aws_inputs = {
            'image_id': self.images['aws'],
            'instance_type': self.build_inputs['aws_instance_type'],
            'vpc_id': self.env.cloudify_config['aws_vpc_id'],
            'vpc_subnet_id': self.env.cloudify_config['aws_subnet_id'],
            'server_name': 'marketplace-system-test-manager',
            'aws_access_key_id': self.build_inputs['aws_access_key'],
            'aws_secret_access_key': self.build_inputs['aws_secret_key'],
            'ec2_region_name': self.build_inputs['aws_region'],
        }

        self.logger.info('initialize local env for running the '
                         'blueprint that starts a vm')
        self.manager_env = local.init_env(
            self.aws_blueprint_yaml,
            inputs=self.aws_inputs,
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

    def _find_image(self):
        conn = self._get_conn()

        image_id = None

        images = conn.get_all_images(owners='self')

        for image in images:
            if image.name.startswith(self.name_prefix):
                image_id = image.id
                break

        return image_id

    def _delete_image(self, image_id):
        conn = self._get_conn()
        image = conn.get_all_images(image_ids=[image_id])[0]
        image.deregister()

    def _delete_agents_keypair(self):
        conn = self._get_conn()
        conn.delete_key_pair(key_name=self.agents_keypair)

    def _delete_agents_secgroup(self):
        conn = self._get_conn()
        sgs = conn.get_all_security_groups()
        candidate_sgs = [
            sg for sg in sgs
            if sg.name == self.agents_secgroup and
            # 'and' is on previous line due to PEP8
            sg.vpc_id == self.env.cloudify_config['aws_vpc_id']
        ]
        if len(candidate_sgs) != 1:
            raise RuntimeError('Could not clean up agents security group')
        else:
            sg_id = candidate_sgs[0].id
            for sg in sgs:
                for rule in sg.rules:
                    groups = [grant.group_id for grant in rule.grants]
                    if sg_id in groups:
                        self._delete_sg_rule_reference(
                            security_group=sg,
                            proto=rule.ip_protocol,
                            from_port=rule.from_port,
                            to_port=rule.to_port,
                            source_sg=candidate_sgs[0],
                        )
            candidate_sgs[0].delete()

    def _delete_sg_rule_reference(self,
                                  security_group,
                                  from_port,
                                  to_port,
                                  source_sg,
                                  proto='tcp'):
        security_group.revoke(
            ip_protocol=proto,
            from_port=from_port,
            to_port=to_port,
            src_group=source_sg,
        )
