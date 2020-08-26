# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import uuid
from msrestazure.azure_exceptions import CloudError
from knack.log import get_logger
from ._util import resolve_poller
from ._client_factory import cf_postgres_firewall_rules, cf_postgres_db, cf_postgres_config
from ._util import generate_missing_parameters

SKU_TIER_MAP = {'Basic': 'b', 'GeneralPurpose': 'gp', 'MemoryOptimized': 'mo'}
logger = get_logger(__name__)


# region create without args
def _flexible_server_create(cmd, client, resource_group_name=None, server_name=None, sku_name=None, tier=None,
                                location=None, storage_mb=None, administrator_login=None,
                                administrator_login_password=None, version=None,
                                backup_retention=None, tags=None, public_network_access=None, vnet_name=None,
                                vnet_address_prefix=None, subnet_name=None, subnet_address_prefix=None, public_access=None,
                                high_availability=None, zone=None, maintenance_window=None, assign_identity=False):
    from azure.mgmt.rdbms import mysql
    db_context = DbContext(
        azure_sdk=mysql, logging_name='MySQL', command_group='mysql', server_client=client)

    try:
        location, resource_group_name, server_name, administrator_login_password = generate_missing_parameters(cmd, location, resource_group_name, server_name, administrator_login_password)
        # The server name already exists in the resource group
        server_result = client.get(resource_group_name, server_name)
        logger.warning('Found existing MySQL Server \'%s\' in group \'%s\'',
                       server_name, resource_group_name)
    except CloudError:
        # Create mysql server
        server_result = _create_server(
            db_context, cmd, resource_group_name, server_name, location, backup_retention,
            sku_name, storage_mb, administrator_login, administrator_login_password, version,
            tags, public_network_access, assign_identity, tier, subnet_name, vnet_name)
    """
    user = '{}@{}'.format(administrator_login, server_name)
    host = server_result.fully_qualified_domain_name
    sku = '{}'.format(sku_name)
    rg = '{}'.format(resource_group_name)
    loc = '{}'.format(location)
    """
    rg = '{}'.format(resource_group_name)
    user = server_result.administrator_login
    id = server_result.id
    loc = server_result.location
    host = server_result.fully_qualified_domain_name
    vsion = server_result.version
    sku = server_result.sku.name

    logger.warning('Make a note of your password. If you forget, you would have to'
                   ' reset your password with CLI command for reset password')

    cmd.cli_ctx.invocation.data['output'] = 'table'

    return _form_response(
    user, sku, loc, rg, id, host,vsion,
        administrator_login_password if administrator_login_password is not None else '*****'
    )


def _create_server(db_context, cmd, resource_group_name, server_name, location, backup_retention, sku_name,
                   storage_mb, administrator_login, administrator_login_password, version,
                   tags, public_network_access, assign_identity, tier, subnet_name, vnet_name):

    logging_name, azure_sdk, server_client = db_context.logging_name, db_context.azure_sdk, db_context.server_client
    logger.warning('Creating %s Server \'%s\' in group \'%s\'...', logging_name, server_name, resource_group_name)

    logger.warning('Your server \'%s\' is using sku \'%s\' (Paid Tier). '
                   'Please refer to https://aka.ms/mysql-pricing for pricing details', server_name, sku_name)

    from azure.mgmt.rdbms import mysql

    # MOLJAIN TO DO: The SKU should not be hardcoded, need a fix with new swagger or need to manually parse sku provided
    parameters = mysql.flexibleservers.models.Server(
        sku=mysql.flexibleservers.models.Sku(name=sku_name, tier=tier),
        administrator_login=administrator_login,
        administrator_login_password=administrator_login_password,
        version=version,
        public_network_access=public_network_access,
        storage_profile=mysql.flexibleservers.models.StorageProfile(
            backup_retention_days=backup_retention,
            # geo_redundant_backup=geo_redundant_backup,
            storage_mb=storage_mb),  ##!!! required I think otherwise data is null error seen in backend exceptions
        # storage_autogrow=auto_grow),
        location=location,
        create_mode="Default",
        vnet_inj_args=mysql.flexibleservers.models.VnetInjArgs(
            delegated_vnet_id=None,  # what should this value be?
            delegated_subnet_name=subnet_name,
            delegated_vnet_name=vnet_name,
            # delegated_vnet_resource_group=None  # what should this value be?
        ),
        tags=tags)

    if assign_identity:
        parameters.identity = mysql.models.flexibleservers.Identity(
            type=mysql.models.flexibleservers.ResourceIdentityType.system_assigned.value)
    # return client.create(resource_group_name, server_name, parameters)

    return resolve_poller(
        server_client.create(resource_group_name, server_name, parameters), cmd.cli_ctx,
        '{} Server Create'.format(logging_name))


def _form_response(username, sku, location, resource_group_name, id, host, version, password):
    return {
        'host': host,
        'username': username,
        'password': password,
        'skuname': sku,
        'location': location,
        'resource group': resource_group_name,
        'id': id,
        'version': version
    }

# pylint: disable=too-many-instance-attributes,too-few-public-methods
class DbContext:
    def __init__(self, azure_sdk=None, logging_name=None,
                 command_group=None, server_client=None):
        self.azure_sdk = azure_sdk
        self.logging_name = logging_name
        self.command_group = command_group
        self.server_client = server_client
