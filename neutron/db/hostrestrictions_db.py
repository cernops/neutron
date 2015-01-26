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

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from oslo.db import exception as db_exc

from neutron.db import common_db_mixin
from neutron.db import model_base
from neutron.db import models_v2
from neutron.db import db_base_plugin_v2 as base_db
from neutron.openstack.common import log as logging
from neutron.openstack.common import uuidutils
from neutron.extensions import hostrestrictions
from neutron.plugins.ml2 import cern
import random
import netaddr

LOG = logging.getLogger(__name__)


class HostRestrictionsDbMixin(hostrestrictions.HostRestrictionsPluginBase,
                              base_db.NeutronDbPluginV2):

    def _make_host_dict(self, hostname, all_subnets, available_subnets, ar_subnet, ma_subnet, la_subnet, fields):
        res = {'hostname': hostname, 
               'all_subnets': all_subnets,
               'available_subnets': available_subnets,
               'available_random_subnet': ar_subnet,
               'most_available_subnet': ma_subnet,
               'least_available_subnet': la_subnet }
        return self._fields(res, fields)

    def _get_subnets_for_host(self, context, hostname):
        client_landb = cern.LanDB()
        clusters = client_landb.vmGetClusterMembership(hostname)
        subnets = []
        for clusterName in clusters:
            cluster = self.get_cluster_by_name(context, clusterName)
            if cluster is not None:
                subnets.extend(cluster['subnets'])
        return subnets

    def _filter_available_subnets(self, context, all_subnets):
        subnets = []
        range_qry = context.session.query(
            models_v2.IPAvailabilityRange).join(
                models_v2.IPAllocationPool)
        for subnet in all_subnets:

            ranges = range_qry.filter_by(subnet_id=subnet).all()

            if not ranges:
                """ If there are no availability ranges, try again after refreshing them """
                self._rebuild_availability_ranges(context, 
                                                 [self._get_subnet(context, subnet)])
                ranges = range_qry.filter_by(subnet_id=subnet).all()
                if not ranges:
                    continue

            subnets.append(subnet)
        return subnets

    def _number_of_allocated_ips(self, context, subnet_id):
        return context.session.query(
            models_v2.IPAllocation).filter_by(subnet_id=subnet_id).count()

    def _number_of_free_ips(self, context, subnet_id):
        pools = context.session.query(
            models_v2.IPAllocationPool).filter_by(subnet_id=subnet_id).all()
        no_of_addresses_in_subnet = 0
        for pool in pools:
            range = netaddr.IPRange(pool['first_ip'], pool['last_ip'])
            no_of_addresses_in_subnet += range.size

        alloc_count = self._number_of_allocated_ips(context, subnet_id)

        return no_of_addresses_in_subnet - alloc_count

    def _find_least_available_subnet(self, context, subnets):
        if subnets:
            la_subnet = subnets[0]
            min_count = self._number_of_free_ips(context, subnets[0])
            for subnet in subnets:
                free_count = self._number_of_free_ips(context, subnet)
                if free_count < min_count and free_count > 0:
                    la_subnet = subnet
                    min_count = free_count
            return la_subnet
        return None

    def _find_most_available_subnet(self, context, subnets):
        if subnets:
            ma_subnet = subnets[0]
            max_count = self._number_of_free_ips(context, subnets[0])
            for subnet in subnets:
                free_count = self._number_of_free_ips(context, subnet)
                if free_count > max_count:
                    ma_subnet = subnet
                    max_count = free_count
            return ma_subnet
        return None

    def get_host(self, context, id, fields=None): 
        hostname = id
        all_subnets = self._get_subnets_for_host(context, hostname)
        available_subnets = self._filter_available_subnets(context, all_subnets)
        random_available_subnet = random.choice(available_subnets)
        most_available_subnet = self._find_most_available_subnet(context, available_subnets)
        least_available_subnet = self._find_least_available_subnet(context, available_subnets)
        return self._make_host_dict(hostname, 
                                    all_subnets, 
                                    available_subnets,
                                    random_available_subnet,
                                    most_available_subnet,
                                    least_available_subnet, 
                                    fields)
