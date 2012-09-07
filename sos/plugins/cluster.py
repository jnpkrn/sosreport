### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import re
from glob import glob


class cluster(Plugin, RedHatPlugin):
    """cluster suite and GFS related information

    Note: corosync has a separate sos plugin.
    """

    optionList = [("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
                  ('lockdump', 'gather dlm lockdumps', 'slow', False)]

    def checkenabled(self):
        rhelver = self.policy().rhelVersion()
        if rhelver == 4:
            self.packages = [ "ccs", "cman", "cman-kernel", "magma", "magma-plugins",
                              "rgmanager", "fence", "dlm", "dlm-kernel", "gulm",
                              "GFS", "GFS-kernel", "lvm2-cluster" ]
        elif rhelver == 5:
            self.packages = [ "rgmanager", "luci", "ricci", "system-config-cluster",
                              "gfs-utils", "gnbd", "kmod-gfs", "kmod-gnbd", "lvm2-cluster", "gfs2-utils" ]

        elif rhelver == 6:
            self.packages = [ "ricci", "corosync", "openais",
                              "cman", "clusterlib", "fence-agents" ]

        self.files = [ "/etc/cluster/cluster.conf" ]
        return Plugin.checkenabled(self)

    def setup(self):
        rhelver = self.policy().rhelVersion()

        if not rhelver or rhelver < 4:
            self.addAlert("cluster sos plugin requires RHEL 4+")
        elif 4 <= rhelver <= 6:
            self.do_setup_pre7(rhelver)
        else:
            self.addAlert("cluster sos plugin does not support RHEL 7 yet")

    def do_setup_pre7(self, rhelver):
        assert 4 <= rhelver <= 6

        # general cluster
        self.addCopySpec("/etc/cluster.conf")
        self.addCopySpec("/etc/cluster.xml")
        self.addCopySpec("/etc/cluster")
        self.addCopySpec("/etc/sysconfig/cluster")
        self.addCopySpec("/var/log/cluster")
        self.collectExtOutput("/usr/sbin/rg_test test /etc/cluster/cluster.conf")

        # cman
        self.addCopySpec("/etc/sysconfig/cman")
        if rhelver == 4:
            self.addCopySpec("/proc/cluster/*")
        else:
            self.collectExtOutput("cman_tool -a nodes")
        self.collectExtOutput("cman_tool services")
        self.collectExtOutput("cman_tool nodes")
        self.collectExtOutput("cman_tool status")
        self.collectOutputNow("clustat")
        self.collectExtOutput("ccs_tool lsnode")

        # locks
        if self.getOption('gfslockdump'):
            self.do_gfslockdump()
        if self.getOption('lockdump'):
            self.do_lockdump(rhelver)

        # dlm
        self.collectExtOutput("dlm_tool log_plock")
        if rhelver == 6:
            self.collectExtOutput("dlm_tool dump")
            self.collectExtOutput("dlm_tool ls -n")

        # group tool
        self.collectOutputNow("group_tool dump")
        if rhelver == 5:
            self.collectExtOutput("group_tool -v")
            self.collectExtOutput("group_tool dump fence")
            self.collectExtOutput("group_tool dump gfs")
        elif rhelver == 6:
            self.collectExtOutput("group_tool ls -g1")

        # fencing
        self.collectExtOutput("fence_tool ls -n")
        self.addCopySpec("/etc/fence_virt.conf")
        if rhelver == 6:
            self.collectExtOutput("fence_tool dump")

        # gfs
        self.collectExtOutput("gfs_control ls -n")
        self.collectExtOutput("/sbin/fdisk -l")
        if rhelver == 6:
            self.collectExtOutput("gfs_control dump")

        # virtual server
        self.collectExtOutput("/sbin/ipvsadm -L")

        # ricci
        self.addCopySpec("/var/lib/ricci")

        # luci
        self.addCopySpec("/etc/sysconfig/luci")  # pre-6, then since 6.1
        if rhelver < 6:
            self.addCopySpec("/var/lib/luci/etc")
            self.addCopySpec("/var/lib/luci/log")
        else:
            self.addCopySpec("/var/log/luci/luci.log")

        # clustermon/modcluster
        self.addCopySpec("/var/log/clumond.log")

    def do_lockdump(self, rhelver):
        assert 4 <= rhelver <= 6

        if rhelver == 4:
            status, output, time = self.callExtProg("cman_tool services")
            for lockspace in re.compile(r'^DLM Lock Space:\s*"([^"]*)".*$', re.MULTILINE).findall(output):
                self.callExtProg("echo %s > /proc/cluster/dlm_locks" % lockspace)
                self.collectOutputNow("cat /proc/cluster/dlm_locks",
                                    suggest_filename="dlm_locks_%s" % lockspace)
        elif rhelver == 5:
            status, output, time = self.callExtProg("group_tool")
            for lockspace in re.compile(r'^dlm\s+[^\s]+\s+([^\s]+)$', re.MULTILINE).findall(output):
                self.collectExtOutput("dlm_tool lockdebug '%s'" % lockspace,
                                      suggest_filename="dlm_locks_%s" % lockspace)
        else:
            status, output, time = self.callExtProg("dlm_tool ls")
            for lockspace in re.compile(r'^name\s+([^\s]+)$', re.MULTILINE).findall(output):
                self.collectExtOutput("dlm_tool lockdebug -svw '%s'" % lockspace,
                                      suggest_filename="dlm_locks_%s" % lockspace)

    def do_gfslockdump(self):
        for mntpoint in self.doRegexFindAll(r'^\S+\s+([^\s]+)\s+gfs\s+.*$', "/proc/mounts"):
            self.collectExtOutput("/sbin/gfs_tool lockdump %s" % mntpoint,
                                  suggest_filename="gfs_lockdump_" + self.mangleCommand(mntpoint))

    def postproc(self):
        # obfuscate passwords for fence devices
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.doRegexSub(cluster_conf, r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")",
                            r"\1%s" % ('"***"'))
