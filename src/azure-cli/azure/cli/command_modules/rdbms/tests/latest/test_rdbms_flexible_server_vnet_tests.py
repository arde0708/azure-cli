# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import time

from azure_devtools.scenario_tests import AllowLargeResponse
from azure.cli.testsdk import (
    NoneCheck,
    ResourceGroupPreparer,
    LocalContextScenarioTest,
    ScenarioTest,
    VirtualNetworkPreparer)

# Constants
SERVER_NAME_PREFIX = 'azuredbclitest-'
SERVER_NAME_MAX_LENGTH = 20


class FlexibleServerLocalContextScenarioTest(LocalContextScenarioTest):

    postgres_location = 'eastus2euap'
    mysql_location = 'eastus2euap'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_local_context(self, resource_group):
        self._test_flexible_server_local_context('postgres', resource_group)


    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_local_context(self, resource_group):
        self._test_flexible_server_local_context('mysql', resource_group)

    def _test_flexible_server_local_context(self, database_engine, resource_group):
        self.cmd('config param-persist on')
        from knack.util import CLIError
        if database_engine == 'mysql':
            location = self.mysql_location
        else:
            location = self.postgres_location

        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        self.cli_ctx.local_context.set(['all'], 'resource_group_name', resource_group)
        self.cli_ctx.local_context.set(['all'], 'location', location)

        self.cmd('{} flexible-server create -n {} --public-access none'.format(database_engine, server_name))

        self.cmd('{} flexible-server show'.format(database_engine))

        self.cmd('{} flexible-server update --backup-retention {}'
                 .format(database_engine, 10))

        self.cmd('{} flexible-server restart'.format(database_engine))

        self.cmd('{} flexible-server stop'.format(database_engine))

        self.cmd('{} flexible-server start'.format(database_engine))

        self.cmd('{} flexible-server list'.format(database_engine))

        self.cmd('{} flexible-server show-connection-string'.format(database_engine))

        self.cmd('{} flexible-server list-skus'.format(database_engine))

        self.cmd('{} flexible-server delete --yes'.format(database_engine))
        self.cmd('config param-persist off')

