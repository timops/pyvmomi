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
   args = parser.parse_args()
   return args

def main():
   """
   Simple command-line program for creating a distributed virtual switch.
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
      hosts = datacenter.networkFolder
      mdvs = pyVmomi.vim.DVSConfigSpec(name=args.vswitch_name)
      dvsconfig = pyVmomi.vim.DVSCreateSpec(configSpec=mdvs)
      hosts.CreateDVS_Task(dvsconfig) 

      print "Creating dvs: ", args.vswitch_name

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
