.. _save-load-layout:

====================
Save and load layout
====================

.. note:: Currently only ``Columns`` support layout saving and loading.

Layout can be saved to and restored from json files using ``save_layout`` and ``load_layout`` commands on the ``Layout`` object.

Window positions, sizes, and in general things that are controlled by ``Layout`` will be saved and restored.

Note ``load-layout`` does not create any windows. Instead, it uses the window matching rules defined in the json file to match against open windows, and apply saved stylings to those matched windows. See `Layout files`_ for more info.

By default qtile will look for layout files in ``CONFIG_DIRECTORY/layouts``, e.g. ``~/.config/qtile/layouts``

Typical workflow
================

To save layout:

- Create some windows

- Save layout using ``save-layout`` command

- Edit the generated json file with more accurate window matching rules

Then to load layout:

- Create the same windows

- Load layout using ``load-layout`` command

``save-layout`` examples
========================

.. code-block:: bash

    # Save current layout to default location (i.e. ~/.config/qtile/layouts/my_layout.json)
    qtile cmd-obj -o layout -f save_layout -a my_layout

    # Save current layout to a specified place
    qtile cmd-obj -o layout -f save_layout -a "/tmp/my_layout.json"

``load-layout`` examples
========================

.. code-block:: bash

    # Load ~/.config/qtile/layouts/my_layout.json
    qtile cmd-obj -o layout -f save_layout -a my_layout

    # Load /tmp/my_layout.json
    qtile cmd-obj -o layout -f load_layout -a "/tmp/my_layout.json"

Layout files
============

Using ``Columns`` as example, the json file produced by ``save_layout`` will look something like:

.. code-block:: json

    {
        "name": "columns",
        "columns": [
            {
                "split": true,
                "insert_position": 0,
                "width": 100,
                "windows": [
                    {
                        "title": "my_window",
                        "wm_type": "...",
                        "wm_class": "...",
                        "role": "...",
                        "focus": true
                    },
                    {
                        "title": "my_other_window",
                        "wm_type": "...",
                        "wm_class": "...",
                        "role": "...",
                        "focus": true
                    }
                ],
                "heights": [
                    100
                ],
                "current": 0
            }
        ]
    }

Most fields such as ``split``, ``insert_position`` are taken directly from the ``Columns`` object. These fields will be used to configure the ``Columns`` object when the layout is loaded.

Each item in ``windows`` is used to create a ``Match`` object. These match objects are used to match against open windows in the current layout. Styling is then applied to matched windows.

E.g. the above layout file will place the window with title "my_window" at the top of first column. Then place "my_other_window" below "my_window" in the same column.

All constructor arguments for ``Match`` are supported:

.. qtile_class:: libqtile.config.Match
    :no-commands:
    :noindex:

Using regex to match windows
============================

Suffix field name with ``_regex`` to use regex matching instead. All fields except ``net_wm_pid`` support ``_regex``.

When both the ``_regex`` and non-regex fields are given, ``_regex`` field takes precedence.

E.g. the following example matches any window with a title that contains "foobar"

.. code-block:: json

    {
        "title_regex": ".*foobar.*"
    }