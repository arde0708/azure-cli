# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from collections import OrderedDict


def table_transform_connection_string(result):
    table_result = []
    for key in ('host', 'username', 'password', 'location', 'skuname', 'resource group', 'id', 'version'):
        entry = OrderedDict()
        entry['Property'] = key
        entry['Value'] = result[key]
        table_result.append(entry)

    return table_result
