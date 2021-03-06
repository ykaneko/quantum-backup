# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2012 Isaku Yamahata <yamahata at private email ne jp>
#                               <yamahata at valinux co jp>
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

import httplib

from nova import flags
from nova import log as logging
from nova.openstack.common import cfg
from nova.virt.libvirt import vif as libvirt_vif
from ryu.app.client import OFPClient

from . import ovs_utils


LOG = logging.getLogger('quantum.plugins.openvswitch.ryu.nova.vif')

ryu_libvirt_ovs_driver_opt = \
    cfg.StrOpt('libvirt_ovs_ryu_api_host',
               default='127.0.0.1:8080',
               help='Openflow Ryu REST API host:port')

FLAGS = flags.FLAGS
FLAGS.add_option(ryu_libvirt_ovs_driver_opt)


class LibvirtOpenVswitchOFPRyuDriver(libvirt_vif.LibvirtOpenVswitchDriver):
    def __init__(self, **kwargs):
        super(LibvirtOpenVswitchOFPRyuDriver, self).__init__()
        LOG.debug('ryu rest host %s', FLAGS.libvirt_ovs_bridge)
        self.ryu_client = OFPClient(FLAGS.libvirt_ovs_ryu_api_host)
        self.datapath_id = ovs_utils.get_datapath_id(FLAGS.libvirt_ovs_bridge)

    def _get_port_no(self, mapping):
        iface_id = mapping['vif_uuid']
        dev = self.get_dev_name(iface_id)
        return ovs_utils.get_port_no(dev)

    def plug(self, instance, network, mapping):
        result = super(LibvirtOpenVswitchOFPRyuDriver, self).plug(
            instance, network, mapping)
        port_no = self._get_port_no(mapping)
        self.ryu_client.create_port(network['id'],
                                    self.datapath_id, port_no)
        return result

    def unplug(self, instance, network, mapping):
        port_no = self._get_port_no(mapping)
        try:
            self.ryu_client.delete_port(network['id'],
                                        self.datapath_id, port_no)
        except httplib.HTTPException as e:
            res = e.args[0]
            if res.status != httplib.NOT_FOUND:
                raise
        super(LibvirtOpenVswitchOFPRyuDriver, self).unplug(instance, network,
                                                           mapping)
