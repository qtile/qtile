# Backend core objects

The backend core is the link between the Qtile objects (windows, layouts, groups etc.)
and the specific backend (X11 or Wayland). This core should be largely invisible to users
and, as a result, these objects do not expose many commands.

Nevertheless, both backends do contain important commands, notably `set_keymap` on X11 and
`change_vt` used to change to a different TTY on Wayland.

The backend core has no access to other nodes on the command graph.

.. qtile_graph::
    :root: core

## X11 backend

::: libqtile.backend.x11.core.Core
    options:
      heading_level: 3
      show_root_full_path: true

## Wayland backend

::: libqtile.backend.wayland.core.Core
    options:
      heading_level: 3
      show_root_full_path: true
