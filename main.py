# The MIT License (MIT)

# Copyright (c) 2015 haidlir

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This is the main component of the application, which acts as the event lsitener
and coordinate each event to other sub-component.
"""
from __future__ import print_function
import time
import thread

from config import config
from bucket import bucket
from lib import *
import routing
import misc
import cli

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.openflow.discovery import Discovery
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.recoco import Timer
from pox.lib.revent import *

class main(EventMixin):
    def __init__(self):
        core.listen_to_dependencies(self, listen_args={'openflow': {'priority':0}})

        Timer(10, self._routing, recurring=True)

    def _routing(self):
        if config.LOCAL_ROUTING == 'DFS':
            bucket.path_list = routing.DFS.findAllPairsPath(bucket.matrix_adj)
        elif config.LOCAL_ROUTING == 'Djisktra':
            pass

    def _send_FlowStatsReq(self):
        pass

    def _periodic_report(self):
        pass

    def _handle_openflow_ConnectionUp(self, event):
        print('DPID %s is UP' % (event.dpid))

        if bucket.matrix_adj.get(event.dpid) is None:
            bucket.matrix_adj[event.dpid] = {}
            bucket.port_info[event.dpid] = {}
            bucket.flow_entry[event.dpid] = {}

        for i,v in enumerate(event.ofp.ports):
            if (v.port_no < 60000):
                bucket.port_info[event.dpid][v.port_no] = PortDetail(i, v.name,
                                                                     v.port_no,
                                                                     v.state,
                                                                     curr_to_capacity(v.curr))

        if config.USE_DHCP:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match()
            msg.match.dl_type = 0x0800  # IP type in 3rd layer
            msg.match.nw_proto = 17  # UDP type in 4th layer
            # msg.match.nw_dst = IP_BROADCAST
            msg.match.tp_src = 68  # DHCP client port
            msg.match.tp_dst = 67  # DHCP server port
            msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
            event.connection.send(msg)

    def _handle_openflow_ConnectionDown(self, event):
        print('DPID %s is DOWN' % (event.dpid))

        if event.dpid in bucket.matrix_adj:
            del bucket.matrix_adj[event.dpid]
        for i in bucket.matrix_adj:
            if event.dpid in bucket.matrix_adj[i]:
                del bucket.matrix_adj[i][event.dpid]

        if event.dpid in bucket.port_info:
            del bucket.port_info[event.dpid]
        if event.dpid in bucket.path_list:
            del bucket.path_list[event.dpid]
        for i in bucket.path_list:
            if event.dpid in bucket.path_list[i]:
                del bucket.path_list[i][event.dpid]
            for j in bucket.path_list[i]:
                temp = []
                for k in bucket.path_list[i][j]:
                    if event.dpid in k.path:
                        temp.append(k)
                bucket.path_list[i][j] = list(set(bucket.path_list[i][j]) - set(temp))

    def _handle_openflow_discovery_LinkEvent(self, event):
        if event.added:
            dpid1 = event.link.dpid1
            dpid2 = event.link.dpid2
            port1 = event.link.port1
            port2 = event.link.port2
            capacity = min(bucket.port_info[dpid1][port1].capacity,
                           bucket.port_info[dpid2][port2].capacity)
            bucket.matrix_adj[dpid1][dpid2] = LinkDetail(dpid1, capacity, port1)
            bucket.matrix_adj[dpid2][dpid1] = LinkDetail(dpid2, capacity, port2)
        elif event.removed:
            print('link discovery timeout')

    def _handle_openflow_PortStatus(self, event):
        dpid = event.dpid
        port_no = event.ofp.desc.port_no
        state = event.ofp.desc.state
        print('port [%s] at dpid[%s] reported' % (port_no, dpid))

        if (event.ofp.desc.state != bucket.port_info[event.dpid][event.ofp.desc.port_no].state):
            bucket.port_info[event.dpid][event.ofp.desc.port_no].state = event.ofp.desc.state
            if (state):
                print('port [%s] at dpid[%s] is Down' % (port_no, dpid))
                if dpid in bucket.gateway:
                    if event.ofp.desc.port_no == bucket.gateway[dpid].port_no:
                        bucket.gateway[dpid].available = False
                        for cookie in bucket.flow_entry[dpid]:
                                if bucket.flow_entry[dpid][cookie].out_port == port_no:
                                   msg = of.ofp_flow_mod()
                                   msg.cookie = cookie
                                   msg.command = of.OFPFC_DELETE
                                   core.openflow.sendToDPID(bucket.flow_entry[dpid][cookie].initial_dpid, msg)          

                if dpid in bucket.matrix_adj:
                    for dpid_next in bucket.matrix_adj[dpid]:
                        if bucket.matrix_adj[dpid][dpid_next].interface == port_no:
                            del bucket.matrix_adj[dpid][dpid_next]
                            break

                    if 'dpid_next' not in locals():
                        return

                    for i in bucket.path_list:
                        for j in bucket.path_list[i]:
                            will_delete = []
                            for k in range(len(bucket.path_list[i][j])):
                                if bucket.path_list[i][j][k].path[0] == dpid_next and i == dpid:
                                   will_delete.append(bucket.path_list[i][j][k])
                                   continue
                                for l in range(len(bucket.path_list[i][j][k].path)-1):
                                    if (bucket.path_list[i][j][k].path[l] == dpid and bucket.path_list[i][j][k].path[l+1] == dpid_next):
                                        will_delete.append(bucket.path_list[i][j][k])
                                        break
                            bucket.path_list[i][j] = list(set(bucket.path_list[i][j]) - set(will_delete))

                    for cookie in bucket.flow_entry[dpid]:
                        for j in range(len(bucket.flow_entry[dpid][cookie].path)-1):
                            if bucket.flow_entry[dpid][cookie].path[j] == dpid and bucket.flow_entry[dpid][cookie].path[j+1] == dpid_next:
                               msg = of.ofp_flow_mod()
                               msg.cookie = cookie
                               msg.command = of.OFPFC_DELETE
                               core.openflow.sendToDPID(bucket.flow_entry[dpid][cookie].initial_dpid, msg)                                        
            else:
                # state = 'up'
                print('port [%s] at dpid[%s] is Up' % (port_no, dpid))
                bucket.port_info[event.dpid][event.ofp.desc.port_no].state = event.ofp.desc.state
                if dpid in bucket.gateway:
                    if event.ofp.desc.port_no == bucket.gateway[dpid].port_no:
                        bucket.gateway[dpid].available = True
               

                # belum selesai, masih mengandalahkan 10s _findPath(), belum realtime ketika hidup

    def _handle_openflow_FlowStatsReceivedS(self, event):
        pass

    def _handle_openflow_PacketIn(self, event):
        pass

def launch():
    core.registerNew(main)
    thread.start_new_thread(cli.cli.main, ())