============
qtile events
============

Prints a feed of fired qtile hooks as JSON lines.

Example:

.. code::

    > qtile events
    {'event_name': 'setgroup', 'args': [], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'layout_change', 'args': [{'name': 'columns'}, {'name': '2', 'windows': [], 'screen': {'index': 0}}], 'kwargs': {}}
    {'event_name': 'client_new', 'args': [{'wid': 3, 'name': 'foot', 'group': None}], 'kwargs': {}}
    {'event_name': 'group_window_add', 'args': [{'name': '2', 'windows': [], 'screen': {'index': 0}}, {'wid': 3, 'name': 'foot', 'group': None}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_managed', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_new', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': None}], 'kwargs': {}}
    {'event_name': 'group_window_add', 'args': [{'name': '2', 'windows': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'screen': {'index': 0}}, {'wid': 4, 'name': 'VLC media player', 'group': None}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_managed', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 4, 'name': 'VLC media player', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_focus_by_click', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 3, 'name': 'foot', 'group': '2'}], 'kwargs': {}}
    {'event_name': 'client_focus', 'args': [{'wid': 2, 'name': 'foot', 'group': '1'}], 'kwargs': {}}
    {'event_name': 'client_mouse_enter', 'args': [{'wid': 2, 'name': 'foot', 'group': '1'}], 'kwargs': {}}
    {'event_name': 'setgroup', 'args': [], 'kwargs': {}}
    {'event_name': 'focus_change', 'args': [], 'kwargs': {}}
    {'event_name': 'layout_change', 'args': [{'name': 'columns'}, {'name': '1', 'windows': [{'wid': 2, 'name': 'foot', 'group': '1'}], 'screen': {'index': 0}}], 'kwargs': {}}
