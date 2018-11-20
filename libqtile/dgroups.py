# Copyright (c) 2011-2012 Florian Mounier
# Copyright (c) 2012-2014 roger
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import collections
import six

import libqtile.hook
from libqtile.config import Key
from libqtile.command import lazy
from libqtile.config import Group
from libqtile.config import Rule
from libqtile.config import Match
from libqtile.log_utils import logger


def simple_key_binder(mod, keynames=None):
    """Bind keys to mod+group position or to the keys specified as second argument"""
    def func(dgroup):
        # unbind all
        for key in dgroup.keys[:]:
            dgroup.qtile.unmapKey(key)
            dgroup.keys.remove(key)

        if keynames:
            keys = keynames
        else:
            # keys 1 to 9 and 0
            keys = list(map(str, list(range(1, 10)) + [0]))

        # bind all keys
        for keyname, group in zip(keys, dgroup.qtile.groups):
            name = group.name
            key = Key([mod], keyname, lazy.group[name].toscreen())
            key_s = Key([mod, "shift"], keyname, lazy.window.togroup(name))
            key_c = Key(
                [mod, "control"],
                keyname,
                lazy.group.switch_groups(name)
            )
            dgroup.keys.append(key)
            dgroup.keys.append(key_s)
            dgroup.keys.append(key_c)
            dgroup.qtile.mapKey(key)
            dgroup.qtile.mapKey(key_s)
            dgroup.qtile.mapKey(key_c)

    return func


class DGroups(object):
    """Dynamic Groups"""
    def __init__(self, qtile, dgroups, key_binder=None, delay=1):
        self.qtile = qtile

        self.groups = dgroups
        self.groupMap = {}

        self.rules = []
        self.rules_map = {}
        self.last_rule_id = 0

        for rule in getattr(qtile.config, 'dgroups_app_rules', []):
            self.add_rule(rule)

        self.keys = []

        self.key_binder = key_binder

        self._setup_hooks()
        self._setup_groups()

        self.delay = delay

        self.timeout = {}

    def add_rule(self, rule, last=True):
        rule_id = self.last_rule_id
        self.rules_map[rule_id] = rule
        if last:
            self.rules.append(rule)
        else:
            self.rules.insert(0, rule)
        self.last_rule_id += 1
        return rule_id

    def remove_rule(self, rule_id):
        rule = self.rules_map.get(rule_id)
        if rule:
            self.rules.remove(rule)
            del self.rules_map[rule_id]
        else:
            logger.warn('Rule "%s" not found', rule_id)

    def add_dgroup(self, group, start=False):
        self.groupMap[group.name] = group
        rules = [Rule(m, group=group.name) for m in group.matches]
        self.rules.extend(rules)
        if start:
            self.qtile.add_group(group.name, group.layout, group.layouts, group.label)

    def _setup_groups(self):
        for group in self.groups:
            self.add_dgroup(group, group.init)

            if group.spawn and not self.qtile.no_spawn:
                if isinstance(group.spawn, six.string_types):
                    spawns = [group.spawn]
                else:
                    spawns = group.spawn
                for spawn in spawns:
                    pid = self.qtile.cmd_spawn(spawn)
                    self.add_rule(Rule(Match(net_wm_pid=[pid]), group.name))

    def _setup_hooks(self):
        libqtile.hook.subscribe.addgroup(self._addgroup)
        libqtile.hook.subscribe.client_new(self._add)
        libqtile.hook.subscribe.client_killed(self._del)
        if self.key_binder:
            libqtile.hook.subscribe.setgroup(
                lambda: self.key_binder(self)
            )
            libqtile.hook.subscribe.changegroup(
                lambda: self.key_binder(self)
            )

    def _addgroup(self, qtile, group_name):
        if group_name not in self.groupMap:
            self.add_dgroup(Group(group_name, persist=False))

    def _add(self, client):
        if client in self.timeout:
            logger.info('Remove dgroup source')
            self.timeout.pop(client).cancel()

        # ignore static windows
        if client.defunct:
            return

        # ignore windows whose groups is already set (e.g. from another hook or
        # when it was set on state restore)
        if client.group is not None:
            return

        group_set = False
        intrusive = False

        for rule in self.rules:
            # Matching Rules
            if rule.matches(client):
                if rule.group:
                    if rule.group in self.groupMap:
                        layout = self.groupMap[rule.group].layout
                        layouts = self.groupMap[rule.group].layouts
                        label = self.groupMap[rule.group].label
                    else:
                        layout = None
                        layouts = None
                        label = None
                    group_added = self.qtile.add_group(rule.group, layout, layouts, label)
                    client.togroup(rule.group)

                    group_set = True

                    group_obj = self.qtile.groupMap[rule.group]
                    group = self.groupMap.get(rule.group)
                    if group and group_added:
                        for k, v in list(group.layout_opts.items()):
                            if isinstance(v, collections.Callable):
                                v(group_obj.layout)
                            else:
                                setattr(group_obj.layout, k, v)
                        affinity = group.screen_affinity
                        if affinity and len(self.qtile.screens) > affinity:
                            self.qtile.screens[affinity].setGroup(group_obj)

                if rule.float:
                    client.enablefloating()

                if rule.intrusive:
                    intrusive = rule.intrusive

                if rule.break_on_match:
                    break

        # If app doesn't have a group
        if not group_set:
            current_group = self.qtile.current_group.name
            if current_group in self.groupMap and \
                    self.groupMap[current_group].exclusive and \
                    not intrusive:

                wm_class = client.window.get_wm_class()

                if wm_class:
                    if len(wm_class) > 1:
                        wm_class = wm_class[1]
                    else:
                        wm_class = wm_class[0]

                    group_name = wm_class
                else:
                    group_name = client.name or 'Unnamed'

                self.add_dgroup(Group(group_name, persist=False), start=True)
                client.togroup(group_name)
        self.sort_groups()

    def sort_groups(self):
        grps = self.qtile.groups
        sorted_grps = sorted(grps, key=lambda g: self.groupMap[g.name].position)
        if grps != sorted_grps:
            self.qtile.groups = sorted_grps
            libqtile.hook.fire("changegroup")

    def _del(self, client):
        group = client.group

        def delete_client():
            # Delete group if empty and don't persist
            if group and group.name in self.groupMap and \
                    not self.groupMap[group.name].persist and \
                    len(group.windows) <= 0:
                self.qtile.delete_group(group.name)
                self.sort_groups()
            del self.timeout[client]

        # Wait the delay until really delete the group
        logger.info('Add dgroup timer')
        self.timeout[client] = self.qtile.call_later(
            self.delay, delete_client
        )
