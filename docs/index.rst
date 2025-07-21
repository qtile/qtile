.. image:: /_static/qtile-logo.svg
    :align: center

=======================================
Everything you need to know about Qtile
=======================================

Qtile is a full-featured, hackable tiling window manager written and configured
in Python. It's available both as an X11 window manager and also as
:ref:`a Wayland compositor <wayland>`.

This documentation is designed to help you :doc:`install <manual/install/index>`
and :doc:`configure <manual/config/index>` Qtile. Once it's up and running you'll
probably want to start adding your own :doc:`customisations <manual/hacking>`
to have it running exactly the way you want.

You'll find a lot of what you need within these docs but, if you still have some
questions, you can find support in the following places:

:Q&A: https://github.com/qtile/qtile/discussions/categories/q-a
:IRC: irc://irc.oftc.net:6667/qtile
:Discord: https://discord.gg/ehh233wCrC (Bridged with IRC)

.. toctree::
    :maxdepth: 1
    :caption: Getting Started
    :hidden:

    manual/install/index
    Wayland <manual/wayland>
    Wayland Status <manual/wayland_status>
    manual/troubleshooting
    manual/commands/shell/index

.. toctree::
    :maxdepth: 1
    :caption: Configuration
    :hidden:

    manual/config/default
    manual/config/index
    manual/ref/layouts
    manual/ref/widgets
    manual/ref/hooks
    manual/ref/extensions
    manual/commands/keybindings
    manual/stacking

.. toctree::
    :maxdepth: 1
    :caption: Scripting
    :hidden:

    manual/commands/index
    manual/commands/interfaces
    manual/commands/api/index

.. toctree::
    :maxdepth: 1
    :caption: Hacking
    :hidden:

    manual/hacking
    manual/contributing

.. toctree::
    :maxdepth: 1
    :caption: Miscellaneous
    :hidden:

    manual/faq
    manual/howto/widget
    manual/howto/layout
    manual/howto/git
    manual/license
    manual/changelog
