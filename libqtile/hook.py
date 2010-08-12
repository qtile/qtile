import manager

hooks = [
    ["setgroup", "Called when group is changed."],
    ["focus_change", "Called when focus is changed."],
    ["group_window_add", "Called when a new window is added to a group."],
    ["window_name_change", "Called whenever a windows name changes."],
    ["client_new", "Called whenever Qtile starts managing a new client."],
    ["client_killed", "Called whenever a client is killed."],
    ["client_state_changed", "Called whenever client state changes."],
    ["client_type_changed", "Called whenever window type changes."],
    ["client_focus", "Called whenver focus changes."],
    ["client_mouse_enter", "Called when the mouse enters a client."],
    ["client_name_updated", "Called when the client name changes."],
    ["client_urgent_hint_changed", "Called when the client urgent hint changes."],
    ["tick", "Called whenever the mainloop ticks."],
]

_hooks = set(i[0] for i in hooks)
subscriptions = {}
SKIPLOG = set(["tick"])

def init(q):
    global qtile
    qtile = q

def clear():
    subscriptions.clear()

def subscribe(event, func):
    if event not in _hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    lst = subscriptions.setdefault(event, [])
    if not func in lst:
        lst.append(func)

def fire(event, *args, **kwargs):
    if event not in _hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    if not event in SKIPLOG:
        qtile.log.add("Internal event: %s(%s, %s)"%(event, args, kwargs))
    for i in subscriptions.get(event, []):
        i(*args, **kwargs)

