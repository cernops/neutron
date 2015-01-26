# Copyright (c) 2015 CERN.
# All Rights Reserved.
#
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

from neutron.db import common_db_mixin
from neutron.db import subnetcluster_db
from neutron.db import hostrestrictions_db
from neutron.services import service_base
from neutron.plugins.common import constants


class CERNServicePlugin(#service_base.ServicePluginBase,
                        subnetcluster_db.SubnetClusterDbMixin,
                        hostrestrictions_db.HostRestrictionsDbMixin):

    supported_extension_aliases = ["subnetcluster", "hostrestrictions"]

    def get_plugin_type(self):
        return constants.CERN

    def get_plugin_name(self):
        return constants.CERN

    def get_plugin_description(self):
        return "CERN Service Plugin that implements subnetcluster and hostrestrictions extension"

