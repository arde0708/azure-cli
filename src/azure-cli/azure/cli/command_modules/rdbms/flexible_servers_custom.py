# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import uuid
from msrestazure.azure_exceptions import CloudError
from knack.log import get_logger
from ._util import resolve_poller
from ._client_factory import cf_postgres_firewall_rules, cf_postgres_db, cf_postgres_config
from azure.mgmt.resource.resources.models import ResourceGroup
from ._client_factory import resource_client_factory
from ._util import create_random_resource_name


SKU_TIER_MAP = {'Basic': 'b', 'GeneralPurpose': 'gp', 'MemoryOptimized': 'mo'}
logger = get_logger(__name__)

DEFAULT_LOCATION = 'eastus2'

# region create without args
def _flexible_server_create(cmd, client, resource_group_name=None, server_name=None, location=None, backup_retention=None,
                                   sku_name=None, geo_redundant_backup=None, storage_mb=None, administrator_login=None,
                                   administrator_login_password=None, version=None, ssl_enforcement=None, database_name=None, tags=None, public_network_access=None, infrastructure_encryption=None,
                                   assign_identity=False):
    from azure.mgmt.rdbms import postgresql
    db_context = DbContext(
        azure_sdk=postgresql, logging_name='PostgreSQL', command_group='postgres', server_client=client)

    try:
        # if location is not passed as a parameter or is missing from local context
        if location is None:
            location = DEFAULT_LOCATION
            cmd.cli_ctx.local_context.set(['all'], 'location', location) # Setting the location in the local context

        # If resource group is there in local context, check for its existence.
        resource_group_exists = True
        if resource_group_name is not None:
            logger.warning('Checking the existence of the resource group \'%s\'...', resource_group_name)
            resource_group_exists = _check_resource_group_existence(cmd, resource_group_name)
            logger.warning('Resource group \'%s\' exists ? : %s ', resource_group_name, resource_group_exists)

        # If resource group is not passed as a param or is not in local context or the rg in the local context has been deleted
        if not resource_group_exists or resource_group_name is None:
            resource_group_name = _create_resource_group(cmd, location, resource_group_name)

        # If servername is not passed, always create a new server - even if it is stored in the local context
        if server_name is None:
            server_name = create_random_resource_name('server')
            #cmd.cli_ctx.local_context.get_value('server-name')
            cmd.cli_ctx.local_context.set(['all'], 'server-name', server_name)  # Setting the location in the local context

        # The server name already exists in the resource group
        server_result = client.get(resource_group_name, server_name)
        logger.warning('Found existing PostgreSQL Server \'%s\' in group \'%s\'',
                       server_name, resource_group_name)

        # update server if needed once we have it like sterling
        '''
        server_result = _update_server(
            db_context, cmd, client, server_result, resource_group_name, server_name, backup_retention,
            geo_redundant_backup, storage_mb, administrator_login_password, version, ssl_enforcement, tags)
        '''
    except CloudError:
        # Create postgresql server
        if administrator_login_password is None:
            administrator_login_password = str(uuid.uuid4())
        server_result = _create_server(
            db_context, cmd, resource_group_name, server_name, location, backup_retention,
            sku_name, geo_redundant_backup, storage_mb, administrator_login, administrator_login_password, version,
            ssl_enforcement, tags, public_network_access, infrastructure_encryption, assign_identity)

    user = '{}@{}'.format(administrator_login, server_name)
    host = server_result.fully_qualified_domain_name
    sku = '{}'.format(sku_name)
    rg = '{}'.format(resource_group_name)
    loc = '{}'.format(location)

    return _form_response(
        host, user, sku, loc, rg,
        administrator_login_password if administrator_login_password is not None else '*****',
        _create_postgresql_connection_string(host, administrator_login_password)
    )


def _create_resource_group(cmd, location, resource_group_name):
    if resource_group_name is None:
        resource_group_name = create_random_resource_name('group')
    params = ResourceGroup(location=location)
    resource_client = resource_client_factory(cmd.cli_ctx)
    logger.warning('Creating Resource Group \'%s\'...', resource_group_name)
    resource_client.resource_groups.create_or_update(resource_group_name, params)
    cmd.cli_ctx.local_context.set(['all'], 'resource_group_name', resource_group_name)
    return resource_group_name


def _check_resource_group_existence(cmd, resource_group_name):
    resource_client = resource_client_factory(cmd.cli_ctx)
    return  resource_client.resource_groups.check_existence(resource_group_name)


def _create_server(db_context, cmd, resource_group_name, server_name, location, backup_retention, sku_name,
                   geo_redundant_backup, storage_mb, administrator_login, administrator_login_password, version,
                   ssl_enforcement, tags, public_network_access, infrastructure_encryption, assign_identity):
    logging_name, azure_sdk, server_client = db_context.logging_name, db_context.azure_sdk, db_context.server_client
    logger.warning('Creating %s Server \'%s\' in group \'%s\'...', logging_name, server_name, resource_group_name)

    logger.warning('Make a note of your password. If you forget, you would have to'
                   ' reset your password with CLI command for reset password')

    logger.warning('Your server \'%s\' is using sku \'%s\' (Paid Tier). '
                   'Please refer to https://aka.ms/postgres-pricing for pricing details', server_name, sku_name)

    from azure.mgmt.rdbms import postgresql

    # MOLJAIN TO DO: The SKU should not be hardcoded, need a fix with new swagger or need to manually parse sku provided
    parameters = postgresql.flexibleservers.models.Server(
        sku=postgresql.flexibleservers.models.Sku(name=sku_name, tier="GeneralPurpose", capacity=4),
        administrator_login=administrator_login,
        administrator_login_password=administrator_login_password,
        version=version,
        ssl_enforcement=ssl_enforcement,
        public_network_access=public_network_access,
        infrastructure_encryption=infrastructure_encryption,
        storage_profile=postgresql.flexibleservers.models.StorageProfile(
            backup_retention_days=backup_retention,
            geo_redundant_backup=geo_redundant_backup,
            storage_mb=storage_mb),  ##!!! required I think otherwise data is null error seen in backend exceptions
        # storage_autogrow=auto_grow),
        location=location,
        create_mode="Default",  # can also be create
        tags=tags)

    if assign_identity:
        parameters.identity = postgresql.models.ResourceIdentity(
            type=postgresql.models.IdentityType.system_assigned.value)

    return resolve_poller(
        server_client.create(resource_group_name, server_name, parameters), cmd.cli_ctx,
        '{} Server Create'.format(logging_name))


def _create_postgresql_connection_string(host, password):
    connection_kwargs = {
        'host': host,
        'password': password if password is not None else '{password}'
    }
    return 'postgres://postgres:{password}@{host}/postgres?sslmode=require'.format(**connection_kwargs)


def _form_response(host, username, sku, location, resource_group_name, password, connection_string):
    return {
        'connection string': connection_string,
        'host': host,
        'username': username,
        'password': password,
        'skuname': sku,
        'location': location,
        'resource group': (resource_group_name),
    }


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class DbContext:
    def __init__(self, azure_sdk=None, logging_name=None,
                 command_group=None, server_client=None):
        self.azure_sdk = azure_sdk
        self.logging_name = logging_name
        self.command_group = command_group
        self.server_client = server_client
