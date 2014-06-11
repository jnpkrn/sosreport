## Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

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

import sos.plugintools

class distupgrade(sos.plugintools.PluginBase):
    """Distribution upgrade information
    """

    packages = [
        'preupgrade-assistant',
        'redhat-upgrade-tool'
    ]

    def setup(self):
	self.addCopySpecs([
            '/root/preupgrade/kickstart',
            '/root/preupgrade/result.html',
            '/root/preupgrade/result.xml',
            '/root/preupgrade/RHEL6_7/all-xccdf.xml',
            '/var/log/redhat_upgrade_tool.log',
            '/var/log/preupgrade/preupg.log',
            '/var/log/preupgrade/ui.log',
            '/var/cache/preupgrade/common'
        ])
        return

    def postproc(self):
        self.doRegexSub(
            "/root/preupgrade/kickstart/anaconda-ks.cfg",
            r"(\s*rootpw\s*).*",
            r"\1********"
        )

        self.doRegexSub(
            "/root/preupgrade/kickstart/untrackeduser",
            r"\/home\/.*",
            r"/home/******** path redacted ********"
        )

        self.doRegexSub(
            "/var/cache/preupgrade/common/allmyfiles.log",
            r"\/home\/.*",
            r"/home/******** path redacted ********"
        )
