# Copyright (c) 2014 CERN
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


import ldap
import time
import random
import socket
import string
import suds.client

from suds.xsd.doctor import ImportDoctor, Import
from suds.client import Client

import logging as pylog
from neutron.plugins.ml2.common import cern_exceptions as exception
from neutron.openstack.common.gettextutils import _
from neutron.openstack.common import log as logging
from oslo.config import cfg


cern_network_opts = [
    cfg.StrOpt('landb_hostname',
        default='', secret=True,
        help='landb hostname'),
    cfg.StrOpt('landb_port',
        default='443', secret=True,
        help='landb port'),
    cfg.StrOpt('landb_protocol',
        default='https', secret=True,
        help='landb protocol'),
    cfg.StrOpt('landb_username',
        default='', secret=True,
        help='landb username'),
    cfg.StrOpt('landb_password',
        default='', secret=True,
        help='landb password')
]

CONF = cfg.CONF
CONF.register_opts(cern_network_opts, 'CERN')

LOG = logging.getLogger(__name__)
pylog.getLogger('suds.client').setLevel(pylog.CRITICAL)


class LanDB:

    def __init__(self, host=None, username=None, password=None, client=None):
        if client != None:
            self.client = client
        else:
            self.client = self.__auth(hostname=None, port=None, protocol=None, username=None, password=None)

    def __auth(self, hostname=None, port=None, protocol=None, username=None, password=None):
        """Authenticates in landb"""
        if username == None or password == None:
            username = CONF.CERN.landb_username
            password = CONF.CERN.landb_password
            hostname = CONF.CERN.landb_hostname
            port = CONF.CERN.landb_port
            protocol = CONF.CERN.landb_protocol

        url = "%s://%s:%s/sc/soap/soap.fcgi?v=5&WSDL" % (protocol, hostname, port)
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        d = ImportDoctor(imp)
        client = Client(url, doctor=d)

        try:
            token = client.service.getAuthToken(username,password,'CERN')
            myheader = dict(Auth={'token':token})
            client.set_options(soapheaders=myheader)
        except Exception as e:
            LOG.error(_("Cannot authenticate in landb: %s" % str(e)))
            raise exception.CernLanDBAuthentication()

        return client

    def vm_create(self, device, ip_service, ip_address, mac_address,
            hypervisor_name, cluster_name, responsible_person,
            location=None, manufacter=None, model=None, description=None, tag=None,
            operating_system=None, user_person=None):

        if location is None:
            location = {'Floor':'0', 'Room':'0', 'Building':'0'}

        if manufacter is None:
            manufacter = 'KVM'

        if model is None:
            model = 'VIRTUAL MACHINE'

        if description is None:
            description = ""

        if tag is None:
            tag = 'OPENSTACK VM'

        if operating_system is None:
            operating_system = {'Name':'LINUX', 'Version': 'UNKNOWN'}

        if user_person is None :
            user_person = responsible_person

        hardware_address = mac_address
        card_type = 'Ethernet'

        parent_host = hypervisor_name

        service_name = ip_service

        internet_connectivity = 'Y'

        try:
            self.client.service.vmCreate(
                        {'DeviceName': device,
                        'Location': location,
                        'Manufacturer': manufacter,
                        'Model': model,
                        'Description': description,
                        'Tag': tag,
                        'OperatingSystem': operating_system,
                        'ResponsiblePerson':responsible_person,
                        'UserPerson':user_person},
                        {'HardwareAddress': hardware_address,
                         'CardType': card_type},
                        cluster_name,
                        parent_host,
                        {'IP': ip_address,
                         'ServiceName': service_name,
                         'InternetConnectivity': internet_connectivity})
        except Exception as e:
            LOG.error(_("Cannot create instance in landb: %s" % str(e)))
            raise exception.CernLanDBUpdate()
        pass

    def vm_update(self, device, new_device=None,
            location=None, manufacter=None, model=None, description=None, tag=None,
            operating_system=None, responsible_person=None, user_person=None):
        """Update vm metadata in landb"""
        metadata = None
        try:
            metadata = self.client.service.getDeviceBasicInfo(device.upper())
        except Exception as e:
            pass

        if new_device == None: new_device = device

        if location == None:
            location = {'Floor':'0', 'Room':'0', 'Building':'0'}

        if manufacter == None:
            manufacter = 'KVM'

        if model == None:
            model = 'VIRTUAL MACHINE'

        if description == None and metadata != None:
            description = metadata.Description if metadata.Description != None\
             else ''

        if tag == None:
            tag = 'OPENSTACK VM'

        if operating_system == None and metadata != None:
            operating_system = metadata.OperatingSystem

        if responsible_person == None and metadata != None:
            responsible_person = metadata.ResponsiblePerson

        if user_person == None and metadata != None:
            user_person = metadata.UserPerson

        try:
            self.client.service.vmUpdate(device,
                        {'DeviceName': new_device,
                        'Location': location,
                        'Manufacturer': manufacter,
                        'Model': model,
                        'Description': description,
                        'Tag': tag,
                        'OperatingSystem': operating_system,
                        'ResponsiblePerson':responsible_person,
                        'UserPerson':user_person})
        except Exception as e:
            LOG.error(_("Cannot update landb: %s" % str(e)))
            raise exception.CernLanDBUpdate()

    def vm_migrate(self, device, parent):
        """Migrate vm to parent"""
        try:
            self.client.service.vmMigrate(device, (parent.lower()).replace('.cern.ch', ''))
            LOG.debug(_("Parent migration to |%s|" % (parent.lower()).replace('.cern.ch', '')))
        except Exception as e:
            LOG.error(_("Cannot migrate VM in landb - %s" % str(e)))

    def vm_delete(self, device):
        """Delete vm from landb"""
        try:
            self.client.service.vmNetReset(device)
            self.client.service.vmDestroy(device)
        except Exception as e:
            LOG.error(_("Cannot delete vm from landb: %s" % str(e)))
            raise exception.CernLanDBUpdate()

    def device_exists(self, device):
        """Check if a device is registered in landb"""
        try:
            self.client.service.getDeviceInfo(device)
        except:
            return False
        return device

    def device_hostname(self, address):
        """Get the hostname given an IP"""
        try:
            device = (self.client.service.searchDevice({'IPAddress':address}))[0]
        except Exception as e:
            LOG.error(_("Cannot find device with IP: %s" % str(e)))
            raise exception.CernDeviceNotFound('')
        return device

    def device_migrate(self, hostname, node):
        """Migrate VM to node"""
        try:
            self.client.service.vmMigrate(hostname, node)
        except Exception as e:
            LOG.error(_("Cannot migrate device in lanDB: %s" % str(e)))
            return False
        return True

    def alias_update(self, device, new_alias):
        """Update alias"""
        try:
            old_alias = self.getDeviceInfo(device).Interfaces[0].IPAliases
            if old_alias == None: old_alias = []

            for alias in new_alias:
                if (alias not in old_alias) and self.device_exists(alias):
                    LOG.error(_("Alias already exists"))
                    raise exception.CernInvalidHostname()

            for alias in old_alias:
                self.__unset_alias(device, alias)

            for alias in new_alias:
                self.__set_alias(device, alias)
        except exception.CernInvalidHostname:
             msg = _("%s - The device already exists or is not "
                     "a valid hostname" % str(alias))
             raise exception.CernInvalidHostname(msg)

    def ipv6ready_update(self, device, boolean):
        """Update ipv6 ready flag"""
        try:
            self.client.service.deviceUpdateIPv6Ready(device, boolean)
        except Exception as e:
            LOG.error(_("Cannot change IPv6-ready: %s" % str(e)))
            raise exception.CernLanDBUpdate()

    def __set_alias(self, device, alias):
        """Set alias to a device"""
        try:
            self.client.service.interfaceAddAlias(device, alias)
        except Exception as e:
            LOG.error(_("Cannot set alias in landb: %s" % str(e)))
            raise exception.CernLanDBUpdate()

    def __unset_alias(self, device, alias):
        """Unset all alias in a device"""
        try:
            self.client.service.interfaceRemoveAlias(device, alias)
        except Exception as e:
            LOG.error(_("Cannot unset alias in landb: %s" % str(e)))
            raise exception.CernLanDBUpdate()

    def vmClusterGetDevices(self, cluster):
        """Get all cluster devices"""
        try:
            return self.client.service.vmClusterGetDevices(cluster)
        except Exception as e:
            LOG.error(_("Cannot get VMs from network cluster - %s - %s"),
                        cluster, str(e))
            raise exception.CernLanDB()

    def vmClusterGetInfo(self, cluster):
        """Get cluster info"""
        try:
            return self.client.service.vmClusterGetInfo(cluster)
        except Exception as e:
            LOG.error(_("Cannot get network services for network cluster - "
                        "%s - %s"), cluster, str(e))
            raise exception.CernLanDB()

    def getServiceInfo(self, service):
        """Get service information"""
        try:
            return self.client.service.getServiceInfo(service)
        except Exception as e:
            LOG.error(_("Cannot get service information"))
            raise exception.CernLanDB()

    def getDevicesFromService(self, service):
        """Get devices from service"""
        try:
            return self.client.service.getDevicesFromService(service)
        except Exception as e:
            LOG.error(_("Cannot devices from service: %s - %s"), service, str(e))
            raise exception.CernLanDB()

    def getDeviceInfo(self, device):
        """Get device information"""
        try:
            return self.client.service.getDeviceInfo(device)
        except Exception as e:
            LOG.error(_("Cannot get VM netwok info - %s" % str(e)))
            raise exception.CernLanDB()

    def vmGetClusterMembership(self, hostname):
        """Gets the list of clusters where this physical host is on"""
        try:
            host = hostname.split(".")[0]
            return self.client.service.vmGetClusterMembership(host)
        except Exception as e:
            LOG.error(_("Cannot get list of clusters: %s - %s"), hostname, str(e))
            raise exception.CernLanDB()


class Xldap:
    def __init__(self, url='xldap.cern.ch', protocol_version=ldap.VERSION3,
                 searchScope=ldap.SCOPE_SUBTREE, retrieveAttributes=None):
        self.client = ldap.open(url)
        self.client.protocol_version = protocol_version
        self.searchScope = searchScope
        self.retrieveAttributes = retrieveAttributes

    def user_exists(self, user, baseDN='OU=Users,OU=Organic Units,DC=cern,DC=ch'):
        """Check if an user exists at CERN"""
        try:
            searchFilter = "cn="+user
            ldap_result_id = self.client.search(baseDN, self.searchScope,
                        searchFilter, self.retrieveAttributes)
            result_type, result_data = self.client.result(ldap_result_id, 0)
            if (result_data == []):
                return False
            if result_type == ldap.RES_SEARCH_ENTRY:
                return int(result_data[0][1]['employeeID'][0])
        except Exception as e:
            LOG.error(_("Cannot verify if USER exists. %s" % str(e)))
            raise exception.CernInvalidUser()

    def egroup_exists(self, egroup, baseDN='OU=Workgroups,DC=cern,DC=ch'):
        """Check if an egroup exists at CERN"""
        try:
            searchFilter = "cn="+egroup
            ldap_result_id = self.client.search(baseDN, self.searchScope,
                        searchFilter, self.retrieveAttributes)
            result_type, result_data = self.client.result(ldap_result_id, 0)
            if (result_data == []):
                return False
            if result_type == ldap.RES_SEARCH_ENTRY:
                return str(egroup)
        except Exception as e:
            LOG.error(_("Cannot verify if EGROUP exists. %s" % str(e)))
            raise exception.CernInvalidEgroup()

    def device_exists(self, device):
        """Check if device exists in Xldap"""
        try:
            searchFilter = "(&(name="+device+"))"
            ldap_result_id = self.client.search(baseDN, self.searchScope,
                        searchFilter, self.retrieveAttributes)
            result_type, result_data = self.client.result(ldap_result_id, 0)
            if (result_data == []):
                return False
            if result_type == ldap.RES_SEARCH_ENTRY:
                return device
        except Exception as e:
            LOG.error(_("Cannot verify if device exists. %s" % str(e)))
            raise exception.CernInvalidDevice()
