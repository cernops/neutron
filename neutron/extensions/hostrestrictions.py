#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import six
import abc

from abc import abstractmethod

from neutron.api import extensions
from neutron import manager
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import base
from neutron.common import exceptions
from neutron.api.v2 import resource_helper
from neutron.plugins.common import constants
from neutron.services import service_base

RESOURCE_NAME = 'host'

RESOURCE_ATTRIBUTE_MAP = {
    RESOURCE_NAME + 's': {
        'hostname': {'allow_post': False, 'allow_put': False,
                 'validate': {'type:string': None},
                 'is_visible': True},
        'all_subnets': {'allow_post': False, 'allow_put': False,
                    'validate': {'type:uuid_list': None},
                    'convert_to': attr.convert_none_to_empty_list,
                    'default': None, 'is_visible': True},
        'available_subnets': {'allow_post': False, 'allow_put': False,
                    'validate': {'type:uuid_list': None},
                    'convert_to': attr.convert_none_to_empty_list,
                    'default': None, 'is_visible': True},
        'available_random_subnet': {'allow_post': False, 'allow_put': False,
                                    'validate': {'type:string': None},
                                    'is_visible': True},
        'most_available_subnet': {'allow_post': False, 'allow_put': False,
                                  'validate': {'type:string': None},
                                  'is_visible': True},
        'least_available_subnet': {'allow_post': False, 'allow_put': False,
                                  'validate': {'type:string': None},
                                  'is_visible': True},
    },
}

class Hostrestrictions(extensions.ExtensionDescriptor):

    @classmethod
    def get_name(cls):
        return "CERN Host Restrictions"

    @classmethod
    def get_alias(cls):
        return "hostrestrictions"

    @classmethod
    def get_description(cls):
        return "Returns information about CERN network host restrictions"

    @classmethod
    def get_namespace(cls):
        return "http://github.com/cernops/neutron"

    @classmethod
    def get_updated(cls):
        return "2015-03-09T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        """Returns Ext Resources."""

        special_mappings = {'hosts': 'host'}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                                   constants.CERN,
                                                   action_map=action_map)

    @classmethod
    def get_plugin_interface(cls):
        return HostRestrictionsPluginBase

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        else:
            return {}

@six.add_metaclass(abc.ABCMeta)
class HostRestrictionsPluginBase(service_base.ServicePluginBase):
    """REST API to operate the host restrictions.

    All of method must be in an admin context.
    """

    @abstractmethod
    def get_host(self, context, id, fields=None):
        pass
