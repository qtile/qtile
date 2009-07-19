import manager

hooks = set(
    [
        "setgroup",
        "focus_change",
        "window_add",
        "window_name_change",
        "client_new",
        "client_killed",
        "client_state_changed",
        "client_type_changed",
        "client_focus",
        "client_mouse_enter",
        "client_name_updated",
        "client_urgent_hint_changed",
        "mainloop_tick",
    ]
)
subscriptions = {}

def init(q):
    global qtile
    qtile = q

def clear():
    subscriptions.clear()

def subscribe(event, func):
    if event not in hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    lst = subscriptions.setdefault(event, [])
    if not func in lst:
        lst.append(func)

def fire(event, *args, **kwargs):
    if event not in hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    qtile.log.add("Internal event: %s(%s, %s)"%(event, args, kwargs))
    for i in subscriptions.get(event, []):
        i(*args, **kwargs)

