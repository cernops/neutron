# Copyright (c) 2015 CERN
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

from oslo_log import log
from novaclient.v1_1 import client as novaclient
from oslo.config import cfg
from neutron.plugins.ml2 import cern
from neutron.plugins.ml2.common import exceptions as ml2_exc
from neutron.plugins.ml2.common import cern_exceptions as cern_exc
from neutron.plugins.ml2 import driver_api as api
from neutron.services.cern import plugin as cernplugin
from landbclient import client as landbclient

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class CERNLanDBMechanismDriver(api.MechanismDriver):

    def initialize(self):
        pass

    def create_port_postcommit(self, context):
        super(CERNLanDBMechanismDriver, self).create_port_postcommit(context)
        # Raising MechanismDriverError here will delete the port from neutron
        if context.current['device_owner'].split(':')[0] == 'compute':
            device_id = context.current['device_id']
            subnet_id = context.current['fixed_ips'][0]['subnet_id']
            ip_addr = context.current['fixed_ips'][0]['ip_address']
            mac_addr = context.current['mac_address']
            hypervisor = context.current['binding:host_id'].split('.')[0]
            ip_service = context._plugin.get_subnet(context._plugin_context,
                                                    subnet_id)['name']
            token = CONF.keystone_authtoken
            compute_client = novaclient.Client(token.admin_user,
                                               token.admin_password,
                                               token.admin_tenant_name,
                                               token.auth_uri,
                                               cacert=token.cafile,
                                               service_type="compute")
            nova_device = compute_client.servers.get(device_id)
            instance = nova_device.name
            user_name = nova_device.user_id

            CERNServPlugin = cernplugin.CERNServicePlugin()
            cluster_name = CERNServPlugin.get_cluster_by_subnet(
                context._plugin_context, subnet_id)['name']

            landb_username = CONF.CERN.landb_username
            landb_password = CONF.CERN.landb_password
            landb_hostname = CONF.CERN.landb_hostname
            landb_port = CONF.CERN.landb_port
            landb_protocol = CONF.CERN.landb_protocol

            client_landb = landbclient.LanDB(username=landb_username,
                                             password=landb_password,
                                             host=landb_hostname,
                                             port=landb_port,
                                             protocol=landb_protocol)
            client_xldap = cern.Xldap()

            person_id = client_xldap.user_exists(user_name)
            if not person_id:
                LOG.error(_("Cannot verify if USER exists: %s" % user_name))
                raise cern_exc.CernInvalidUser()
            landb_responsible = {'PersonID': person_id}
            landb_mainuser = {'PersonID': person_id}

            if client_landb.device_exists(instance):
                LOG.error(_("CERN_LANDB: instance with hostname %(instance)s"
                          "already exists"), {'instance': instance})
                raise ml2_exc.MechanismDriverError()
            else:

                try:
                    client_landb.vm_create(device=instance,
                                    ip_service=ip_service,
                                    ip_address=ip_addr,
                                    mac_address=mac_addr,
                                    hypervisor_name=hypervisor,
                                    cluster_name=cluster_name,
                                    responsible_person=landb_responsible,
                                    user_person=landb_mainuser)
                    LOG.debug(_("CERN_LANDB: instance %(instance)s created"),
                              {'instance': instance})
                except cern_exc.CernLanDBUpdate:
                    LOG.error(_("CERN_LANDB: failed to create entry for"
                        "instance %(device)s, ip=%(ip)s, mac=%(mac)s on"
                        "hypervisor %(hv)s and ip service %(ips)s"),
                        {'device': instance, 'ip': ip_addr, 'mac': mac_addr,
                         'hv': hypervisor, 'ips': ip_service})
                    raise ml2_exc.MechanismDriverError()
        else:
            LOG.error(_("CERN_LANDB: attempted creation of port with owner not"
                "nova: %(own)"), {'own': context.current['device_owner']})
            # raise ml2_exc.MechanismDriverError()

    def delete_port_postcommit(self, context):
        super(CERNLanDBMechanismDriver, self).delete_port_postcommit(context)
        # Raising an exception here will NOT prevent
        # the port from being deleted
        if context.current['device_owner'].split(':')[0] == 'compute':
            ip_address = context.current['fixed_ips'][0]['ip_address']

            landb_username = CONF.CERN.landb_username
            landb_password = CONF.CERN.landb_password
            landb_hostname = CONF.CERN.landb_hostname
            landb_port = CONF.CERN.landb_port
            landb_protocol = CONF.CERN.landb_protocol

            client_landb = landbclient.LanDB(username=landb_username,
                                             password=landb_password,
                                             host=landb_hostname,
                                             port=landb_port,
                                             protocol=landb_protocol)
            try:
                instance = client_landb.device_search(ip_address)
                client_landb.vm_delete(instance)
                LOG.debug(_("CERN_LANDB: instance %(instance)s deleted"),
                          {'instance': instance})
            except cern_exc.CernLanDBUpdate:
                LOG.error(_("CERN_LANDB: failed to delete instance"
                    "%(instance)s"), {'instance': instance})
                raise ml2_exc.MechanismDriverError()
            except cern_exc.CernDeviceNotFound:
                LOG.error(_("CERN_LANDB: instance %(instance)s with IP %(ip)s"
                    "not found"), {'instance': instance, 'ip': ip_address})
                raise ml2_exc.MechanismDriverError()
        else:
            LOG.error(_("CERN_LANDB: attempted deletion of port with"
                "owner not nova: %(own)"),
                {'own': context.current['device_owner']})
            # raise ml2_exc.MechanismDriverError()
