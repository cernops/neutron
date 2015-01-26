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

"""Custom CERN exceptions."""

from neutron.common import exceptions


class CernProjectTargetCell(exceptions.NeutronException):
    message = _("Failed to select available cell.")


class CernDNS(exceptions.NeutronException):
    message = _("Failed to update DNS.")


class CernNetwork(exceptions.NeutronException):
    message = _("Network inconsistency.")


class CernHostnameWrong(exceptions.NeutronException):
    message = _("Invalid hostname.")


class CernInvalidHostname(exceptions.NeutronException):
    message = _("Device already exists or is not a valid hostname.")
    code = 404


class CernInvalidUser(exceptions.NeutronException):
    message = _("Invalid user.")
    code = 404


class CernInvalidEgroup(exceptions.NeutronException):
    message = _("Invalid egroup.")
    code = 404


class CernInvalidUserEgroup(exceptions.NeutronException):
    message = _("Invalid user or egroup.")
    code = 404


class CernInvalidDevice(exceptions.NeutronException):
    message = _("Invalid device.")
    code = 404


class CernDeviceNotFound(exceptions.NeutronException):
    message = _("Device not found.")


class CernLanDB(exceptions.NeutronException):
    message = _("Unable to connect to LanDB")


class CernLanDBAuthentication(exceptions.NeutronException):
    message = _("Unable to authenticate to LanDB")


class CernLanDBUpdate(exceptions.NeutronException):
    message = _("Unable to update LanDB")


class CernActiveDirectory(exceptions.NeutronException):
    message = _("Network Error")
