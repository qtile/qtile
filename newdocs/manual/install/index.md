# Installation

## Distro Guides

Below are the preferred installation methods for specific distros. If you are
running something else, please see [Installing From Source][installing-from-source].

## Installing From Source

### Python interpreters

We aim to always support the last three versions of CPython, the reference
Python interpreter. We usually support the latest stable version of [PyPy][] as
well. You can check the versions and interpreters we currently run our test
suite against in our [tox configuration file][].

There are not many differences between versions aside from Python features you
may or may not be able to use in your config. PyPy should be faster at runtime
than any corresponding CPython version under most circumstances, especially for
bits of Python code that are run many times. CPython should start up faster than
PyPy and has better compatibility for external libraries.

[tox configuration file]: https://github.com/qtile/qtile/blob/master/tox.ini
[PyPy]: https://www.pypy.org/


### Core Dependencies

Here are Qtile's core runtime dependencies and the package names that provide them 
in Ubuntu. Note that Qtile can run with one of two backends -- X11 and Wayland -- so 
only the dependencies of one of these is required.

+----------------------+-------------------------+------------------------------------------+
| Dependency           | Ubuntu Package          |  Needed for                              |
+======================+=========================+==========================================+
|                        **Core Dependencies**                                              |
+----------------------+-------------------------+------------------------------------------+
| [CFFI][]             | python3-cffi            | Bars and popups                          |
+----------------------+-------------------------+------------------------------------------+
| [cairocffi][]        | python3-cairocffi       | Drawing on bars and popups (if using     |
|                      |                         | X11 install xcffib BEFORE installing     |
|                      |                         | cairocffi, see below)                    |
+----------------------+-------------------------+------------------------------------------+
| libpangocairo        | libpangocairo-1.0-0     | Writing on bars and popups               |
+----------------------+-------------------------+------------------------------------------+
| [dbus-next][]        | --                      | Sending notifications with dbus          |
|                      |                         | (optional).                              |
+----------------------+-------------------------+------------------------------------------+
|                        **X11**                                                            |
+----------------------+-------------------------+------------------------------------------+
| X server             | xserver-xorg            |  X11 backends                            |
+----------------------+-------------------------+------------------------------------------+
| [xcffib][]           | python3-xcffib          |  required for X11 backend                |
+----------------------+-------------------------+------------------------------------------+
|                        **Wayland**                                                        |
+----------------------+-------------------------+------------------------------------------+
| [wlroots][]          | libwlroots-dev          |  Wayland backend (see below)             |
+----------------------+-------------------------+------------------------------------------+
| [pywlroots][]        | --                      |  python bindings for the wlroots library |
+----------------------+-------------------------+------------------------------------------+
| [pywayland][]        | --                      |  python bindings for the wayland library |
+----------------------+-------------------------+------------------------------------------+
| [python-xkbcommon][] | --                      |  required for wayland backeds            |
+----------------------+-------------------------+------------------------------------------+

[CFFI]: https://cffi.readthedocs.io/en/latest/installation.html
[xcffib]: https://github.com/tych0/xcffib#installation
[wlroots]: https://gitlab.freedesktop.org/wlroots/wlroots
[pywlroots]: https://github.com/flacjacket/pywlroots
[pywayland]: https://pywayland.readthedocs.io/en/latest/install.html
[python-xkbcommon]: https://github.com/sde1000/python-xkbcommon
[cairocffi]: https://cairocffi.readthedocs.io/en/stable/overview.html
[dbus-next]: https://python-dbus-next.readthedocs.io/en/latest/index.html

### cairocffi

Qtile uses [cairocffi][] for drawing on status bars and popup windows. Under X11,
cairocffi requires XCB support via xcffib, which you should be sure to have
installed **before** installing cairocffi; otherwise, the needed cairo-xcb
bindings will not be built. Once you've got the dependencies installed, you can
use the latest version on PyPI:

```bash
pip install --no-cache-dir cairocffi
```

### Qtile

With the dependencies in place, you can now install the stable version of qtile from PyPI:

```bash
pip install qtile
```

Or with sets of dependencies:

```bash
pip install qtile[wayland]  # for Wayland dependencies
pip install qtile[widgets]  # for all widget dependencies
pip install qtile[all]      # for all dependencies
```

Or install qtile-git with:

```bash
git clone https://github.com/qtile/qtile.git
cd qtile
pip install .
```

As long as the necessary libraries are in place, this can be done at any point,
however, it is recommended that you first install xcffib to ensure the
cairo-xcb bindings are built (X11 only) (see above).

## Starting Qtile

There are several ways to start Qtile. The most common way is via an entry in
your X session manager's menu. The default Qtile behavior can be invoked by
creating a [qtile.desktop](https://github.com/qtile/qtile/blob/master/resources/qtile.desktop)
file in `/usr/share/xsessions`.

A second way to start Qtile is a custom X session. This way allows you to
invoke Qtile with custom arguments, and also allows you to do any setup you
want (e.g. special keyboard bindings like mapping caps lock to control, setting
your desktop background, etc.) before Qtile starts. If you're using an X
session manager, you still may need to create a `custom.desktop` file similar
to the `qtile.desktop` file above, but with `Exec=/etc/X11/xsession`. Then,
create your own `~/.xsession`. There are several examples of user defined
`xsession` s in the [qtile-examples](https://github.com/qtile/qtile-examples) repository.

If there is no display manager such as SDDM, LightDM or other and there is need
to start Qtile directly from `~/.xinitrc` do that by adding 
`exec qtile start` at the end.

In very special cases, ex. Qtile crashing during session, then suggestion would
be to start through a loop to save running applications:

```bash
while true; do
    qtile
done
```

Finally, if you're a gnome user, you can start integrate Qtile into Gnome's
session manager and use gnome as usual.

- [Running from systemd](without-dm.md)
- [Running inside Gnome](gnome.md)

## Wayland

Qtile can be run as a Wayland compositor rather than an X11 window manager. For
this, Qtile uses [wlroots][], a compositor library which is undergoing fast
development. Be aware that some distributions package outdated versions of
wlroots. More up-to-date distributions such as Arch Linux may package
pywayland, pywlroots and python-xkbcommon. Also note that we may not have yet
caught up with the latest wlroots release ourselves.

NOTE: We currently support wlroots==0.16.0,<0.17.0 and pywlroots==0.16.4.

With the Wayland dependencies in place, Qtile can be run either from a TTY, or
within an existing X11 or Wayland session where it will run inside a nested
window:

```bash
qtile start -b wayland
```

See the [Wayland](../wayland.md) page for more information on running Qtile as
a Wayland compositor.

Similar to the xsession example above, a wayland session file can be used to start qtile
from a login manager. To use this, you should create
a [qtile-wayland.desktop](https://github.com/qtile/qtile/blob/master/resources/qtile-wayland.desktop)
file in `/usr/share/wayland-sessions`.
