==========
qtile repl
==========

Creates a REPL (Read-Evaluate-Print-Loop) client with access to the qtile internals.

The client requires the `prompt_toolkit <https://pypi.org/project/prompt_toolkit/>`__
library to work.

The client has support for code completion, multiline input and input history.

Example:

.. code::

    > qtile repl
    Connected to Qtile REPL
    Press Ctrl+C to exit.
    >>> qtile.current_group
    <group.Group ('2')>
    >>> qtile.groups_map["3"].toscreen()
    >>> qtile.current_window.name
    'Alacritty'
    >>> def switch_group(name):
    ...   if name not in qtile.groups_map:
    ...       print(f"Unknown group: {name}")
    ...   else:
    ...       qtile.groups_map[name].toscreen()
    ...
    ...
    >>> switch_group("q")
    Unknown group: q
    >>> switch_group("1")
