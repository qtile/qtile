import itertools
import gobject

import libqtile.hook
from libqtile.config import Key
from libqtile.command import lazy
from libqtile.config import Group
from libqtile.config import Rule

def simple_key_binder(mod, keynames=None):
    """
        Bind keys to mod+group position or to the keys specified as
        second argument.
    """
    def func(dgroup):
        # unbind all
        for key in dgroup.keys[:]:
            dgroup.qtile.unmapKey(key)
            dgroup.keys.remove(key)

        if keynames:
            keys = keynames
        else:
            # keys 1 to 9 and 0
            keys = map(str, range(1, 10) + [0])

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
    """ Dynamic Groups """
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
        self.rules_map[self.last_rule_id] = rule
        if last:
            self.rules.append(rule)
        else:
            self.rules.insert(0, rule)
        self.last_rule_id += 1
        return self.last_rule_id

    def remove_rule(self, rule_id=None):
        rule = self.rules[rule_id]
        self.rules.remove(rule)
        del self.rules[rule_id]

    def add_dgroup(self, group, start=False):
        self.groupMap[group.name] = group
        rules = [Rule(m, group=group.name) for m in group.matches]
        self.rules.extend(rules)
        if start:
            self.qtile.addGroup(group.name, group.layout, group.layouts)

    def _setup_groups(self):
        for group in self.groups:
            self.add_dgroup(group, group.init)

            if group.spawn and not self.qtile.no_spawn:
                self.qtile.cmd_spawn(group.spawn)

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
            self.qtile.log.info('Remove dgroup source')
            gobject.source_remove(self.timeout[client])
            del(self.timeout[client])

        # ignore static windows
        if client.defunct:
            return

        group_set = False
        intrusive = False

        for rule in self.rules:
            # Matching Rules
            if rule.matches(client):
                if rule.group:
                    try:
                        layout = self.groupMap[rule.group].layout
                    except KeyError:
                        layout = None
                    group_added = self.qtile.addGroup(rule.group, layout)
                    client.togroup(rule.group)

                    group_set = True

                    group_obj = self.qtile.groupMap[rule.group]
                    group = self.groupMap.get(rule.group)
                    if group and group_added:
                        for k, v in group.layout_opts.iteritems():
                            if callable(v):
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
            current_group = self.qtile.currentGroup.name
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
        self.qtile.groups.sort(key=lambda g: self.groupMap[g.name].position)
        libqtile.hook.fire("setgroup")

    def _del(self, client):
        group = client.group

        def delete_client():
            # Delete group if empty and dont persist
            if group and group.name in self.groupMap and \
                    not self.groupMap[group.name].persist and \
                    len(group.windows) <= 0:
                self.qtile.delGroup(group.name)
                self.sort_groups()

        # Wait the delay until really delete the group
        self.qtile.log.info('Add dgroup timer')
        self.timeout[client] = gobject.timeout_add_seconds(
            self.delay,
            delete_client
        )
