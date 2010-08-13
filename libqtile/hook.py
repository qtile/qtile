import manager

subscriptions = {}
SKIPLOG = set(["tick"])

def init(q):
    global qtile
    qtile = q

def clear():
    subscriptions.clear()


class Subscribe:
    def __init__(self):
        hooks = set([])
        for i in dir(self):
            if not i.startswith("_"):
                hooks.add(i)
        self.hooks = hooks
        
    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        if not func in lst:
            lst.append(func)

    def setgroup(self, func):
        """
            Called when group is changed.
        """
        return self._subscribe("setgroup", func)

    def focus_change(self, func):
        """
            Called when focus is changed.
        """
        return self._subscribe("focus_change", func)

    def group_window_add(self, func):
        """
            Called when a new window is added to a group.
        """
        return self._subscribe("group_window_add", func)

    def window_name_change(self, func):
        """
            Called whenever a windows name changes.
        """
        return self._subscribe("window_name_change", func)

    def client_new(self, func):
        """
            Called whenever Qtile starts managing a new client.
        """
        return self._subscribe("client_new", func)

    def client_killed(self, func):
        """
            Called whenever a client is killed.
        """
        return self._subscribe("client_killed", func)

    def client_state_changed(self, func):
        """
            Called whenever client state changes.
        """
        return self._subscribe("client_state_changed", func)

    def client_type_changed(self, func):
        """
            Called whenever window type changes.
        """
        return self._subscribe("client_type_changed", func)

    def client_focus(self, func):
        """
            Called whenver focus changes.
        """
        return self._subscribe("client_focus", func)

    def client_mouse_enter(self, func):
        """
            Called when the mouse enters a client.
        """
        return self._subscribe("client_mouse_enter", func)

    def client_name_updated(self, func):
        """
            Called when the client name changes.
        """
        return self._subscribe("client_name_updated", func)

    def client_urgent_hint_changed(self, func):
        """
            Called when the client urgent hint changes.
        """
        return self._subscribe("client_urgent_hint_changed", func)

    def tick(self, func):
        """
            Called whenever the mainloop ticks.
        """
        return self._subscribe("tick", func)

subscribe = Subscribe()

def fire(event, *args, **kwargs):
    if event not in subscribe.hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    if not event in SKIPLOG:
        qtile.log.add("Internal event: %s(%s, %s)"%(event, args, kwargs))
    for i in subscriptions.get(event, []):
        i(*args, **kwargs)

