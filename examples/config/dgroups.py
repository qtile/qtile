import libqtile.hook


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
                value = client.window.get_wm_class()[1]
            elif _type == 'wm_type':
                value = client.window.get_wm_type()
            else:
                value = client.window.get_wm_window_role()

            if match_func(value):
                return True
        return False


class DGroups(object):
    ''' Dynamic Groups '''
    def __init__(self, qtile, groups, apps, config=None):
        self.qtile = qtile

        self.groups = groups
        self.apps = apps

        self.config = config

        self._setup_hooks()
        self._setup_groups()

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

    def _add(self, client):
        for app in self.apps:
            # Matching Rules
            if app['match'].compare(client):
                if 'group' in app:
                    group = app['group']
                    self.qtile.addGroup(group)
                    client.togroup(group)

                if 'float' in app and app['float']:
                    client.floating = True
                return

        # Unmatched
        current_group = self.qtile.currentGroup.name
        if current_group in self.groups and\
                self.groups.get(current_group, 'exclusive'):

            wm_class = client.window.get_wm_class()

            self.qtile.addGroup(wm_class[1])
            client.togroup(wm_class[1])

    def _del(self, client):
        group = client.group

        # Delete group if empty and no persist
        if not (group.name in self.groups and\
           self.groups[group.name].get('persist')) and\
                               len(group.windows) == 1:
            self.qtile.delGroup(group.name)
