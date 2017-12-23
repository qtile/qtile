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

import asyncio  # noqa: F401
import itertools
from typing import Callable, Dict, List  # noqa: F401

import libqtile.hook
from libqtile.command import lazy
from libqtile.config import Key, Group, Rule, Match
from libqtile.group import _Group
from libqtile.log_utils import logger


def simple_key_binder(mod, keynames=None) -> Callable:
    """Bind keys to mod+group position or to the keys specified as second argument"""
    def func(dgroup):
        # unbind all
        for key in dgroup.keys[:]:
            dgroup.qtile.unmap_key(key)
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
            dgroup.qtile.map_key(key)
            dgroup.qtile.map_key(key_s)
            dgroup.qtile.map_key(key_c)

    return func


class GroupManager:
    def __init__(self, qtile, groups: List[Group], key_binder=None, delay=1) -> None:
        self.qtile = qtile

        self._groups_map = {group.name: group for group in groups}
        self.active_groups = []  # type: List[_Group]
        self.active_groups_map = {}  # type: Dict[str, _Group]

        self.rules = []  # type: List[Rule]
        self.rules_map = {}  # type: Dict[int, Rule]
        self._rule_id_iter = itertools.count()

        for rule in getattr(qtile.config, 'dgroups_app_rules', []):
            self.add_rule(rule)

        self.keys = []  # type: List[Key]

        self.key_binder = key_binder

        self._setup_hooks()
        self._setup_groups(groups)

        self.delay = delay

        self._timeout = {}  # type: Dict[str, asyncio.TimerHandle]

    def sort_groups(self) -> None:
        grps = self.active_groups
        sorted_grps = sorted(grps, key=lambda g: self._groups_map[g.name].position)
        if grps != sorted_grps:
            self.qtile.groups = sorted_grps
            libqtile.hook.fire("changegroup")

    def add_dgroup(self, group: Group, start=False) -> None:
        self._groups_map[group.name] = group
        for m in group.matches:
            self.add_rule(Rule(m, group=group.name))
        if start:
            self.add_group(group.name, layout=group.layout, layouts=group.layouts, label=group.label)

    def add_group(self, name: str, *, layout=None, layouts=None, label=None):
        if name not in self.active_groups_map.keys():
            g = _Group(name, layout, label=label)
            self.active_groups.append(g)
            if not layouts:
                layouts = self.qtile.config.layouts
            g._configure(layouts, self.qtile.config.floating_layout, self.qtile)
            self.active_groups_map[name] = g
            libqtile.hook.fire("addgroup", self.qtile, name)
            libqtile.hook.fire("changegroup")
            self.qtile.update_net_desktops()

            return True
        return False

    def delete_group(self, name: str) -> None:
        if len(self.active_groups_map) == len(self.qtile.screens):
            raise ValueError("Can't delete all groups.")
        if name in self.active_groups_map.keys():
            group = self.active_groups_map[name]
            if group.screen and group.screen.previous_group:
                target = group.screen.previous_group
            else:
                target = group.get_previous_group()

            # Find a group that's not currently on a screen to bring to the
            # front. This will terminate because of our check above.
            while target.screen:
                target = target.get_previous_group()

            for i in list(group.windows):
                i.togroup(target.name)
            if self.qtile.current_group.name == name:
                self.qtile.current_screen.set_group(target, save_prev=False)
            self.active_groups.remove(group)
            del self.active_groups_map[name]
            libqtile.hook.fire("delgroup", self.qtile, name)
            libqtile.hook.fire("changegroup")
            self.qtile.update_net_desktops()

    def add_rule(self, rule: Rule, last=True) -> int:
        rule_id = next(self._rule_id_iter)
        self.rules_map[rule_id] = rule
        if last:
            self.rules.append(rule)
        else:
            self.rules.insert(0, rule)
        return rule_id

    def remove_rule(self, rule_id: int) -> None:
        rule = self.rules_map.get(rule_id)
        if rule:
            self.rules.remove(rule)
            del self.rules_map[rule_id]
        else:
            logger.warn('Rule "%s" not found', rule_id)

    def _setup_groups(self, groups: List[Group]) -> None:
        for group in groups:
            for match in group.matches:
                self.add_rule(Rule(match, group=group.name))

            if group.init:
                self.add_group(group.name, layout=group.layout, layouts=group.layouts, label=group.label)

            if group.spawn and not self.qtile.no_spawn:
                if isinstance(group.spawn, str):
                    spawns = [group.spawn]
                else:
                    spawns = group.spawn
                for spawn in spawns:
                    pid = self.qtile.cmd_spawn(spawn)
                    self.add_rule(Rule(Match(net_wm_pid=[pid]), group.name))

    def _setup_hooks(self) -> None:
        libqtile.hook.subscribe.addgroup(self._addgroup_hook)
        libqtile.hook.subscribe.client_new(self._add_client_hook)
        libqtile.hook.subscribe.client_killed(self._del_client_hook)
        if self.key_binder:
            libqtile.hook.subscribe.setgroup(
                lambda: self.key_binder(self)
            )
            libqtile.hook.subscribe.changegroup(
                lambda: self.key_binder(self)
            )

    def _addgroup_hook(self, qtile, group_name) -> None:
        if group_name not in self._groups_map:
            group = Group(group_name, persist=False)
            self._groups_map[group.name] = group

    def _add_client_hook(self, client) -> None:
        if client.name in self._timeout:
            logger.info('Remove dgroup source')
            self._timeout.pop(client.name).cancel()

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
                    if rule.group in self._groups_map:
                        layout = self._groups_map[rule.group].layout
                        layouts = self._groups_map[rule.group].layouts
                        label = self._groups_map[rule.group].label
                    else:
                        layout = None
                        layouts = None
                        label = None
                    group_added = self.add_group(rule.group, layout=layout, layouts=layouts, label=label)
                    client.togroup(rule.group)

                    group_set = True

                    group_obj = self.qtile._groups_map[rule.group]
                    group = self._groups_map.get(rule.group)
                    if group and group_added:
                        for k, v in list(group.layout_opts.items()):
                            if callable(v):
                                v(group_obj.layout)
                            else:
                                setattr(group_obj.layout, k, v)
                        affinity = group.screen_affinity
                        if affinity and len(self.qtile.screens) > affinity:
                            self.qtile.screens[affinity].set_group(group_obj)

                if rule.float:
                    client.enablefloating()

                if rule.intrusive:
                    intrusive = rule.intrusive

                if rule.break_on_match:
                    break

        # If app doesn't have a group
        if not group_set:
            current_group = self.qtile.current_group.name
            if current_group in self._groups_map and \
                    self._groups_map[current_group].exclusive and \
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

    def _del_client_hook(self, client) -> None:
        """Hook that fires on client removal"""
        group = client.group

        def delete_client():
            # Delete group if empty and don't persist
            if group and group.name in self._groups_map and \
                    not self._groups_map[group.name].persist and \
                    len(group.windows) <= 0:
                self.qtile.delete_group(group.name)
                self.sort_groups()
            del self._timeout[client.name]

        # Wait the delay until really delete the group
        logger.info('Add dgroup timer')
        self._timeout[client.name] = self.qtile.call_later(
            self.delay, delete_client
        )
