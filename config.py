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
This component contains all information which manually configured 
by administrator to tune the application.
"""

from __future__ import print_function

class config(object):
    USE_DHCP = True
    USE_STATIC_IP = False
    USE_VLAN = False

    # Ethernet Routing (choose one): {'DFS', 'Dijkstra'}
    LOCAL_ROUTING = 'Dijkstra'

    # contains entries of switch used as gateway
    USE_GATEWAY = False

    USE_OSPF = False
    OSPF_GATEWAY = {}

    USE_BGP = False
    BGP_GATEWAY = {}

    USE_STATIC_GATEWAY = True
    STATIC_GATEWAY = {}