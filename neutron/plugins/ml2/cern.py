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
from neutron.i18n import _
from oslo_log import log as logging
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
