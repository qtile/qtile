Installing on Gentoo
====================

Prepare Dependencies
--------------------

You may apply these USE-Flags:

.. code-block:: bash

    echo "dev-python/pycairo xcb" >> /etc/portage/package.use
    echo "x11-libs/cairo X glib opengl svg xcb" >> /etc/portage/package.use

Install
-------

Simply unmask and emerge:

.. code-block:: bash

    echo "x11-wm/qtile ~amd64" >> /etc/portage/package.keywords
    emerge -av qtile

Don't forget the config.py:

.. code-block:: bash

    mkdir ~/.config/qtile
    cp build/lib/libqtile/resources/default_config.py ~/.config/qtile/config.py

where build is i.e

.. code-block:: bash

    /usr/lib64/python2.7/site-packages

Test Installation
-----------------

You can test your installation in Xephyr. If you don't have Xephyr you need to
set the kdrive USE-Flag for xorg-server

.. code-block:: bash

    echo "x11-base/xorg-server kdrive" >> /etc/portage/package.use
    emerge -1 xorg-server

You can run Xephyr with

.. code-block:: bash

    Xephyr :1 -screen 800x600 -av -noreset

In another term you set DISPLAY to :1

.. code-block:: bash

    DISPLAY=:1

You start qtile simply with:

.. code-block:: bash

    qtile

