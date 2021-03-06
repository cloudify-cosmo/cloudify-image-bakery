########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from cosmo_tester.test_suites.test_blueprints.hello_world_bash_test import \
    AbstractHelloWorldTest

from .abstract_aws_test import AbstractAwsTest
from .abstract_packer_test import AbstractSecureTest


class AWSHelloWorldTest(
        AbstractAwsTest,
        AbstractHelloWorldTest,
        ):
    pass


class AWSHelloWorldSecureTest(
        AbstractSecureTest,
        AWSHelloWorldTest,
        ):
    pass
