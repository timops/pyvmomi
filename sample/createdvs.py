#!/usr/bin/python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python script to create dVS.
"""

from optparse import OptionParser, make_option
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
import pyVmomi

import argparse
import atexit
import sys


def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description='Process args for ')
   parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443,   action='store', help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store', help='Password to use when connecting to host')
   parser.add_argument('-v', '--vswitch_name', required=True, action='store', help='Name of dvs to create')
   parser.add_argument('-n', '--numports', required=True, action='store', help='Number of ports in portgroup')
   args = parser.parse_args()
   return args

def AddHosts(nodes, newdvs):
  hypervisors = []
  dvsHostMember = []
  pnicStr = 'vmnic1'
  pnicspec = []

  # this API is required to uniquely configure *each* physical NIC.
  pnicspec.append(pyVmomi.vim.DistributedVirtualSwitchHostMemberPnicSpec(pnicDevice=pnicStr))

  # pnicspec is an array of physical NICs, although in this example only one is added (see above).
  pnic = pyVmomi.vim.DistributedVirtualSwitchHostMemberPnicBacking(pnicSpec=pnicspec)

  for compute in nodes:
    # both a cluster and a single hypervisor has a node attribute (array of hosts object),
    #   so treat them the same
    if hasattr(compute, 'host'):
      for node in compute.host:
        hypervisors.append(node)

  # create a list of host object references (the ones that we wish to add to the DVS).
  for esx in hypervisors:
    print "[LOG]: adding hypervisor %s to the DVS" % (esx.name)
    dvsHostMember.append(pyVmomi.vim.DistributedVirtualSwitchHostMemberConfigSpec(backing=pnic, host=esx, operation='add'))

  dvsConfig = pyVmomi.vim.DVSConfigSpec(configVersion=newdvs.config.configVersion, host=dvsHostMember) 

  # run it against the vCenter
  task = newdvs.ReconfigureDvs_Task(dvsConfig)

def main():
   """
   Simple command-line program for creating a distributed virtual switch and portgroup.
   """

   args = GetArgs()
   try:
      si = None
      try:
         si = SmartConnect(host=args.host,
                user=args.user,
                pwd=args.password,
                port=int(args.port))
      except IOError, e:
        pass
      if not si:
         print "Could not connect to the specified host using specified username and password"
         return -1

      atexit.register(Disconnect, si)

      content = si.RetrieveContent()
      root = content.rootFolder
      datacenter = content.rootFolder.childEntity[0]
      hosts = datacenter.hostFolder.childEntity

      # create a new dvs
      networks = datacenter.networkFolder
      mdvs = pyVmomi.vim.DVSConfigSpec(name=args.vswitch_name)


      dvsconfig = pyVmomi.vim.DVSCreateSpec(configSpec=mdvs)
      dvs_task = networks.CreateDVS_Task(dvsconfig)

      print "Creating dvs: ", args.vswitch_name

      # 
      # Create DVS and poll for status of creation.
      # If it fails, exit because we can't really do anything else.
      #
      # Failure scenario is pretty verbose, but the details are there! :)
      #
      curr_state = ''
      while (not dvs_task.info.result):
        if (curr_state != str(dvs_task.info.state)):
          curr_state = str(dvs_task.info.state)
          print "Current status of creation - [%s]" % (curr_state)
        if (curr_state == 'error'):
          print "\n[ERROR]: failed to create dvs %s" % (args.vswitch_name)
          print "reason - %s" % (dvs_task.info.error)
          return -1

      newdvs = dvs_task.info.result

      pgname = "%s-PG" % (args.vswitch_name)

      # earlyBinding - A free DistributedVirtualPort will be selected and assigned to a
      #    VirtualMachine when the virtual machine is reconfigured to connect to the portgroup.
      # ephemeral - A DistributedVirtualPort will be created and assigned to a VirtualMachine when
      #    the virtual machine is powered on, and will be deleted when the virtual machine is powered off.
      #    An ephemeral portgroup has no limit on the number of ports that can be a part of this portgroup.

      print "\nAdding port group to dvs: ", args.vswitch_name
      pgconfig = pyVmomi.vim.DVPortgroupConfigSpec(name=pgname, numPorts=int(args.numports), type='earlyBinding')
      pg_task = newdvs.CreateDVPortgroup_Task(pgconfig)

      curr_state = ''
      while (not pg_task.info.result):
        if (curr_state != str(pg_task.info.state)):
          curr_state = str(pg_task.info.state)
          print "Current status of creation - [%s]" % (curr_state)
        if (curr_state == 'error'):
          print "\n[ERROR]: failed to add portgroup to dvs %s" % (args.vswitch_name)
          print "reason - %s" % (pg_task.info.error)
          return -1

      AddHosts(hosts, newdvs)

   except vmodl.MethodFault, e:
      print "Caught vmodl fault : " + e.msg
      return -1
   except Exception, e:
      print "Caught exception : " + str(e)
      return -1

   return 0

# Start program
if __name__ == "__main__":
   main()
