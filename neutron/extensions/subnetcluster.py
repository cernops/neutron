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

import abc
import six
from abc import abstractmethod
from neutron.api import extensions
from neutron import manager
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import base
from neutron.common import exceptions
from neutron.api.v2 import resource_helper
from neutron.plugins.common import constants
from neutron.services import service_base

class ClusterExists(exceptions.NeutronException):
    message = _("Subnet cluster with name %(name)s already exist.")

class ClusterNotFound(exceptions.NotFound):
    message = _("Router %(router_id)s could not be found.")

class SubnetInOtherCluster(exceptions.NeutronException):
    message = _("Subnet %(subnet)s is already assigned to another cluster.")

class SubnetNotInCluster(exceptions.NotFound):
    message = _("Cluster %(cluster)s does not contain subnet %(subnet)s.")

class SubnetAlreadyInCluster(exceptions.NeutronException):
    message = _("Cluster %(cluster)s already contains subnet %(subnet)s.")


RESOURCE_NAME = 'cluster'

RESOURCE_ATTRIBUTE_MAP = {
    RESOURCE_NAME + 's': {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': None},
                 'is_visible': True},
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'required_by_policy': True,
                      'validate': {'type:string': None},
                      'is_visible': True},
        'subnets': {'allow_post': True, 'allow_put': True,
                    'validate': {'type:uuid_list': None},
                    'convert_to': attr.convert_none_to_empty_list,
                    'default': None, 'is_visible': True},
    },
}

class Subnetcluster(extensions.ExtensionDescriptor):

    @classmethod
    def get_name(cls):
        return "Subnet Cluster"

    @classmethod
    def get_alias(cls):
        return "subnetcluster"

    @classmethod
    def get_description(cls):
        return "Allows grouping of subnets into clusters"

    @classmethod
    def get_namespace(cls):
        return "http://github.com/cernops/neutron"

    @classmethod
    def get_updated(cls):
        return "2015-01-15T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        """Returns Ext Resources."""

        special_mappings = {'clusters': 'cluster'}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {'cluster': {'insert_subnet': 'PUT',
                                  'remove_subnet': 'PUT'}}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                                   constants.CERN,
                                                   action_map=action_map)

    @classmethod
    def get_plugin_interface(cls):
        return SubnetClusterPluginBase

    def update_attributes_map(self, attributes):
        super(Subnetcluster, self).update_attributes_map(
            attributes, extension_attrs_map=RESOURCE_ATTRIBUTE_MAP)

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        else:
            return {}


@six.add_metaclass(abc.ABCMeta)
class SubnetClusterPluginBase(service_base.ServicePluginBase):
    """REST API to operate the Subnet Clusters.

    All of method must be in an admin context.
    """

    @abstractmethod
    def create_cluster(self, context, cluster):
        pass

    @abstractmethod
    def delete_cluster(self, context, id):
        pass

    @abstractmethod
    def update_cluster(self, context, id, cluster):
        pass

    @abstractmethod
    def get_clusters(self, context, filters=None, fields=None):
        pass

    @abstractmethod
    def get_cluster(self, context, id, fields=None):
        pass

    @abstractmethod
    def insert_subnet(self, context, id, body):
        pass

    @abstractmethod
    def remove_subnet(self, context, id, body):
        pass
