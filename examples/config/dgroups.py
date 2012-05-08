import gobject

import libqtile.hook
from libqtile.manager import Key
from libqtile.command import lazy


class Match(object):
    ''' Match for dynamic groups
        it can match by title, class or role '''
    def __init__(self, title=[], wm_class=[], role=[], wm_type=[]):
        self._rules = [('title', t) for t in title]
        self._rules += [('wm_class', w) for w in wm_class]
        self._rules += [('role', r) for r in  role]
        self._rules += [('wm_type', r) for r in  wm_type]

    def compare(self, client):
        for _type, rule in self._rules:
            match_func = getattr(rule, 'match', None) or\
                         getattr(rule, 'count')

            if _type == 'title':
                value = client.name
            elif _type == 'wm_class':
                value = client.window.get_wm_class()
                if value and len(value)>1:
                    value = value[1]
                elif value:
                    value = value[0]
            elif _type == 'wm_type':
                value = client.window.get_wm_type()
            else:
                value = client.window.get_wm_window_role()

            if value and match_func(value):
                return True
        return False



def simple_key_binder(mod):
    ''' Bind keys to mod+group position '''
    def func(dgroup):
        # unbind all
        for key in dgroup.keys[:]:
            dgroup.qtile.unmapKey(key)
            dgroup.keys.remove(key)

        # keys 1 to 9 and 0
        keynumbers = range(1,10) + [0]

        # bind all keys
        for num, group in zip(keynumbers, dgroup.qtile.groups[:10]):
            name = group.name
            key = Key([mod], str(num), lazy.group[name].toscreen())
            key_s = Key([mod, "shift"], str(num), lazy.window.togroup(name))
            dgroup.keys.append(key)
            dgroup.keys.append(key_s)
            dgroup.qtile.mapKey(key)
            dgroup.qtile.mapKey(key_s)

    return func


class DGroups(object):
    ''' Dynamic Groups '''
    def __init__(self, qtile, groups, apps, key_binder=None, delay=1):
        self.qtile = qtile

        self.groups = groups
        self.apps = apps
        self.keys = []

        self.key_binder = key_binder

        self._setup_hooks()
        self._setup_groups()

        self.delay = delay

        self.timeout = {}

    def _setup_groups(self):
        for name, tag in self.groups.iteritems():
            if tag.get('init') == True:
                self.qtile.addGroup(name)

            spawn_cmd = tag.get('spawn')
            if spawn_cmd:
                self.qtile.cmd_spawn(spawn_cmd)

    def _setup_hooks(self):
        libqtile.hook.subscribe.client_new(self._add)
        libqtile.hook.subscribe.client_killed(self._del)
        if self.key_binder:
            libqtile.hook.subscribe.addgroup(
                    lambda: self.key_binder(self))
            libqtile.hook.subscribe.delgroup(
                    lambda: self.key_binder(self))

    def shuffle_groups(self, lst, match):
        masters = []
        for client in lst:
            if match.compare(client):
                masters.append(client)
        for master in masters:
            lst.remove(master)
            lst.insert(0, master)

    def _add(self, client):
        if client in self.timeout:
            gobject.source_remove(self.timeout[client])
            del(self.timeout[client])
        group_set = False
        intrusive = False

        for app in self.apps:
            # Matching Rules
            if app['match'].compare(client):
                if 'group' in app:
                    group = app['group']
                    self.qtile.addGroup(group)
                    client.togroup(group)

                    group_set = True

                    group_obj = self.qtile.groupMap[group]
                    group_opts = self.groups.get(group)
                    if group_opts:
                        layout = group_opts.get('layout')
                        master = group_opts.get('master')
                        if layout:
                            group_obj.layout = layout
                        if master:
                            group_obj.layout.shuffle(
                                   lambda lst: self.shuffle_groups(lst, master))

                if 'float' in app and app['float']:
                    client.floating = True

                if 'intrusive' in app:
                    intrusive = app['intrusive']

        # If app doesn't have a group
        if not group_set:
            current_group = self.qtile.currentGroup.name
            if current_group in self.groups and\
                    self.groups[current_group].get('exclusive') and\
                    not intrusive:

                wm_class = client.window.get_wm_class()

                if wm_class:
                    if len(wm_class) > 1:
                        wm_class = wm_class[1]
                    else:
                        wm_class = wm_class[0]

                    group_name = wm_class
                else:
                    group_name = client.name

                self.qtile.addGroup(group_name)
                client.togroup(group_name)

    def _del(self, client):
        group = client.group
        def delete_client():
            # Delete group if empty and dont persist
            if group and not (group.name in self.groups and\
               self.groups[group.name].get('persist')) and\
                                   len(group.windows) <= 0:
                self.qtile.delGroup(group.name)

        # wait the delay until really delete the group
        self.timeout[client] = gobject.timeout_add_seconds(self.delay,
                                                         delete_client)
