Installing Qtile
================

Distro Guides
-------------

Below are the preferred installation methods for specific distros. If you are
running something else, please see `Installing From Source`_.

* :doc:`/manual/install/arch`
* :doc:`/manual/install/funtoo`
* :doc:`/manual/install/gentoo`
* :doc:`/manual/install/ubuntu`

Installing From Source
----------------------

Qtile relies on some cutting-edge features in PyCairo, XCB, and xpyb. Until the
latest versions of these projects make it into distros, it's best to use recent
checkouts from their repositories.

Here is a brief step-by-step guide to installing Qtile and its dependencies
from source:

:doc:`/manual/install/source`


Once You've Installed
---------------------

Once you've installed there are several ways to start Qtile. The most common
way is via an entry in your X session manager's menu. The default Qtile
behavior can be invoked by creating a `qtile.desktop
<https://github.com/qtile/qtile/blob/master/resources/qtile.desktop>`_ file in
``/usr/share/xsessions``.

A second way to start Qtile is a custom X session. This way allows you to
invoke Qtile with custom arguments, and also allows you to do any setup you
want (e.g. special keyboard bindings like mapping caps lock to control, setting
your desktop background, etc.) before Qtile starts. If you're using an X
session manager, you still may need to create a ``custom.desktop`` file similar
to the ``qtile.desktop`` file above, but with ``Exec=/etc/X11/xsession``. Then,
create your own ``~/.xsession``. There are several examples of user defined
``xsession`` s in the `qtile-examples
<https://github.com/qtile/qtile-examples>`_ repository.
