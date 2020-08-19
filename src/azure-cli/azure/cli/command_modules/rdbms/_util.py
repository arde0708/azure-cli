# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import random
from knack.config import CLIConfig
from azure.cli.core.commands import AzArgumentContext
from azure.cli.core.commands import LongRunningOperation, _is_poller

CONFIG_DIR = os.path.expanduser(os.path.join('~', '.rdbms'))
ENV_VAR_PREFIX = 'AZEXT'
POSTGRES_CONFIG_SECTION = 'postgres_up'
CONFIG_MAP = {
    'postgres': POSTGRES_CONFIG_SECTION,
}
DB_CONFIG = CLIConfig(config_dir=CONFIG_DIR, config_env_var_prefix=ENV_VAR_PREFIX)


class RdbmsArgumentContext(AzArgumentContext):  # pylint: disable=too-few-public-methods

    def __init__(self, command_loader, scope, **kwargs):    # pylint: disable=unused-argument
        super(RdbmsArgumentContext, self).__init__(command_loader, scope)
        self.validators = []

    def expand(self, dest, model_type, group_name=None, patches=None):
        super(RdbmsArgumentContext, self).expand(dest, model_type, group_name, patches)

        from knack.arguments import ignore_type

        # Remove the validator and store it into a list
        arg = self.command_loader.argument_registry.arguments[self.command_scope].get(dest, None)
        if not arg:  # when the argument context scope is N/A
            return

        self.validators.append(arg.settings['validator'])
        dest_option = ['--__{}'.format(dest.upper())]
        if dest == 'parameters':
            from .validators import get_combined_validator
            self.argument(dest,
                          arg_type=ignore_type,
                          options_list=dest_option,
                          validator=get_combined_validator(self.validators))
        else:
            self.argument(dest, options_list=dest_option, arg_type=ignore_type, validator=None)


def resolve_poller(result, cli_ctx, name):
    if _is_poller(result):
        return LongRunningOperation(cli_ctx, 'Starting {}'.format(name))(result)
    return result

def create_random_resource_name(prefix='azure', length=15):
    append_length = length - len(prefix)
    digits = [str(random.randrange(10)) for i in range(append_length)]
    return prefix + ''.join(digits)


def get_config_value(db_type, option, fallback='_fallback_none'):
    config_section = CONFIG_MAP[db_type]
    if fallback == '_fallback_none':
        result = DB_CONFIG.get(config_section, option)
    else:
        result = DB_CONFIG.get(config_section, option, fallback=fallback)
    if result:
        return result
    return None


def set_config_value(db_type, option, value):
    config_section = CONFIG_MAP[db_type]
    DB_CONFIG.set_value(config_section, option, value)