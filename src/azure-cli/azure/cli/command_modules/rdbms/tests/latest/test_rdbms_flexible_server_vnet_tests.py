# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import time

from azure_devtools.scenario_tests import AllowLargeResponse
from azure.cli.testsdk import (
    NoneCheck,
    ResourceGroupPreparer,
    ScenarioTest,
    VirtualNetworkPreparer)


class FlexibleServerVnetMgmtScenarioTest(ScenarioTest):

    postgres_location = 'eastus2euap'
    mysql_location = 'eastus2euap'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @VirtualNetworkPreparer(location=mysql_location)
    def test_mysql_flexible_server_vnet_mgmt_supplied_subnetid(self, resource_group):
        # Provision a server with supplied Subnet ID that exists, where the subnet is not delegated
        self._test_flexible_server_vnet_mgmt_existing_supplied_subnetid('mysql', resource_group)
        # Provision a server with supplied Subnet ID whose vnet exists, but subnet does not exist and the vnet does not contain any other subnet
        self._test_flexible_server_vnet_mgmt_non_existing_supplied_subnetid('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @VirtualNetworkPreparer(location=postgres_location)
    def test_postgres_flexible_server_vnet_mgmt_supplied_subnetid(self, resource_group):
        # Provision a server with supplied Subnet ID that exists, where the subnet is not delegated
        self._test_flexible_server_vnet_mgmt_existing_supplied_subnetid('postgres', resource_group)
        # Provision a server with supplied Subnet ID whose vnet exists, but subnet does not exist and the vnet does not contain any other subnet
        self._test_flexible_server_vnet_mgmt_non_existing_supplied_subnetid('postgres', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_vnet_mgmt_supplied_vnet(self, resource_group):
        self._test_flexible_server_vnet_mgmt_supplied_vnet('postgres', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_vnet_mgmt_supplied_vnet(self, resource_group):
        self._test_flexible_server_vnet_mgmt_supplied_vnet('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @VirtualNetworkPreparer(parameter_name='virtual_network', location=postgres_location)
    def test_postgres_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, resource_group, virtual_network):
        self._test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname('postgres', resource_group, virtual_network)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @VirtualNetworkPreparer(parameter_name='virtual_network', location=mysql_location)
    def test_mysql_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, resource_group, virtual_network):
        self._test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname('mysql', resource_group, virtual_network)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location, parameter_name='resource_group_1')
    @ResourceGroupPreparer(location=postgres_location, parameter_name='resource_group_2')
    def test_postgres_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, resource_group_1, resource_group_2):
        self._test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg('postgres', resource_group_1, resource_group_2)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location, parameter_name='resource_group_1')
    @ResourceGroupPreparer(location=mysql_location, parameter_name='resource_group_2')
    def test_mysql_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, resource_group_1, resource_group_2):
        self._test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg('mysql', resource_group_1, resource_group_2)

    def _test_flexible_server_vnet_mgmt_existing_supplied_subnetid(self, database_engine, resource_group):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('local-context off')
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = self.mysql_location

        server = 'testvnetserver1' + database_engine

        # Scenario : Provision a server with supplied Subnet ID that exists, where the subnet is not delegated

        subnet_id = self.cmd('network vnet subnet show -g {rg} -n default --vnet-name {vnet}').get_output_in_json()['id']

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --subnet {} -l {}'
                 .format(database_engine, resource_group, server, subnet_id, location))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, server)).get_output_in_json()
        self.assertEqual(show_result_1['delegatedSubnetArguments']['subnetArmResourceId'], subnet_id)
        # delete server
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server),
                 checks=NoneCheck())

    def _test_flexible_server_vnet_mgmt_non_existing_supplied_subnetid(self, database_engine, resource_group):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('local-context off')

        vnet_name_2 = 'clitestvnet1'
        subnet_name_2 = 'clitestsubnet1'
        server = 'testvnetserver2' + database_engine
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = self.mysql_location

        # Scenario : Provision a server with supplied Subnet ID whose vnet exists, but subnet does not exist and the vnet does not contain any other subnet
        # The subnet name is the default created one, not the one in subnet ID
        self.cmd('{} flexible-server create -g {} -n {} -l {} --subnet {}'
                 .format(database_engine, resource_group, server, location, '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(self.get_subscription_id(), resource_group, vnet_name_2, subnet_name_2)))

        # flexible-server show to validate delegation is added to both the created server
        show_result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server)).get_output_in_json()

        self.assertEqual(show_result['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, vnet_name_2, 'Subnet' + server[6:]))

        # Cleanup
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server), checks=NoneCheck())
        # This is required because the delegations cannot be removed until the server is completely deleted. In the current implementation, there is a delay. Hence, the wait
        time.sleep(15 * 60)
        # remove delegations from vnet
        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group,
                                                                                                         'Subnet' + server[6:],
                                                                                                         vnet_name_2))
        # remove  vnet
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group, vnet_name_2))

    def _test_flexible_server_vnet_mgmt_supplied_vnet(self, database_engine, resource_group):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('local-context off')

        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = self.mysql_location

        vnet_name = 'clitestvnet2'
        address_prefix = '10.0.0.0/16'
        subnet_prefix_1 = '10.0.0.0/24'
        vnet_name_2 = 'clitestvnet3'

        # flexible-servers
        servers = ['testvnetserver3' + database_engine, 'testvnetserver4' + database_engine]

        # Case 1 : Provision a server with supplied Vname that exists.

        # create vnet and subnet. When vnet name is supplied, the subnet created will be given the default name.
        vnet_result = self.cmd('network vnet create -n {} -g {} -l {} --address-prefix {} --subnet-name {} --subnet-prefix {}'
                               .format(vnet_name, resource_group, location, address_prefix, 'Subnet' + servers[0][6:], subnet_prefix_1)).get_output_in_json()

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --vnet {} -l {}'
                 .format(database_engine, resource_group, servers[0], vnet_result['newVNet']['name'], location))

        # Case 2 : Provision a server with a supplied Vname that does not exist.
        self.cmd('{} flexible-server create -g {} -n {} --vnet {} -l {}'
                 .format(database_engine, resource_group, servers[1], vnet_name_2, location))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[0])).get_output_in_json()

        show_result_2 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[1])).get_output_in_json()

        self.assertEqual(show_result_1['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, vnet_name, 'Subnet' + servers[0][6:]))

        self.assertEqual(show_result_2['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, vnet_name_2, 'Subnet' + servers[1][6:]))

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[1]),
                 checks=NoneCheck())

        time.sleep(15 * 60)

        # remove delegations from all vnets
        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group,
                                                                                                         'Subnet' + servers[0][6:],
                                                                                                         vnet_name))

        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group,
                                                                                                         'Subnet' + servers[1][6:],
                                                                                                         vnet_name_2))

        # remove all vnets
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group, vnet_name))
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group, vnet_name_2))

    def _test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, database_engine, resource_group, virtual_network):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('local-context off')

        vnet_name_2 = 'clitestvnet6'
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = self.mysql_location

        # flexible-servers
        servers = ['testvnetserver5' + database_engine, 'testvnetserver6' + database_engine]

        # Case 1 : Provision a server with supplied Vname and subnet name that exists.

        # create vnet and subnet. When vnet name is supplied, the subnet created will be given the default name.
        subnet_id = self.cmd('network vnet subnet show -g {rg} -n default --vnet-name {vnet}').get_output_in_json()[
            'id']
        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --vnet {} -l {} --subnet default'
                 .format(database_engine, resource_group, servers[0], virtual_network, location))

        # Case 2 : Provision a server with a supplied Vname and subnet name that does not exist.
        self.cmd('{} flexible-server create -g {} -n {} -l {} --vnet {}'
                 .format(database_engine, resource_group, servers[1], location, vnet_name_2))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[0])).get_output_in_json()

        show_result_2 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[1])).get_output_in_json()

        self.assertEqual(show_result_1['delegatedSubnetArguments']['subnetArmResourceId'], subnet_id)

        self.assertEqual(show_result_2['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, vnet_name_2, 'Subnet' + servers[1][6:]))

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[1]),
                 checks=NoneCheck())

        time.sleep(15 * 60)

        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group,
                                                                                                         'Subnet' + servers[1][6:],
                                                                                                         vnet_name_2))

        # remove all vnets
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group, vnet_name_2))

    def _test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, database_engine, resource_group_1, resource_group_2):
        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('local-context off')

        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = self.mysql_location

        vnet_name = 'clitestvnet7'
        subnet_name = 'clitestsubnet7'
        address_prefix = '10.0.0.0/16'
        subnet_prefix_1 = '10.0.0.0/24'
        vnet_name_2 = 'clitestvnet8'
        subnet_name_2 = 'clitestsubnet8'

        # flexible-servers
        servers = ['testvnetserver7' + database_engine, 'testvnetserver8' + database_engine]

        # Case 1 : Provision a server with supplied subnetid that exists in a different RG

        # create vnet and subnet.
        vnet_result = self.cmd(
            'network vnet create -n {} -g {} -l {} --address-prefix {} --subnet-name {} --subnet-prefix {}'
            .format(vnet_name, resource_group_1, location, address_prefix, subnet_name,
                    subnet_prefix_1)).get_output_in_json()

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} -l {} --subnet {}'
                 .format(database_engine, resource_group_2, servers[0], location, vnet_result['newVNet']['subnets'][0]['id']))

        # Case 2 : Provision a server with supplied subnetid that has a different RG in the ID but does not exist. The vnet and subnet is then created in the RG of the server
        self.cmd('{} flexible-server create -g {} -n {} -l {} --subnet {}'
                 .format(database_engine, resource_group_2, servers[1], location, '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group_1, vnet_name_2, subnet_name_2)))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group_2, servers[0])).get_output_in_json()

        show_result_2 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group_2, servers[1])).get_output_in_json()

        self.assertEqual(show_result_1['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group_1, vnet_name, subnet_name))

        self.assertEqual(show_result_2['delegatedSubnetArguments']['subnetArmResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group_2, vnet_name_2, 'Subnet' + servers[1][6:]))

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group_2, servers[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group_2, servers[1]),
                 checks=NoneCheck())

        time.sleep(15 * 60)

        # remove delegations from all vnets
        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group_1,
                                                                                                         subnet_name,
                                                                                                         vnet_name))

        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group_2,
                                                                                                         'Subnet' +
                                                                                                         servers[1][6:],
                                                                                                         vnet_name_2))

        # remove all vnets
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group_1, vnet_name))
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group_2, vnet_name_2))
