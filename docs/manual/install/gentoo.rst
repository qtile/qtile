Installing on Gentoo
====================

Prepare Dependencies
--------------------

cairo
~~~~~

You may apply these USE-Flags:  X, glib, opengl, svg and xcb to cairo

.. code-block:: bash

    echo "x11-libs/cairo X glib opengl svg xcb" >> /etc/portage/package.use

py2cairo
~~~~~~~~

.. code-block:: bash

    echo "dev-python/pycairo ~amd64 > /etc/portage/package.mask"
    echo "dev-python/pycairo xcb > /etc/portage/package.use"

Install
-------

Simply unmask and install it

.. code-block:: bash

    echo "x11-wm/qtile ~amd64 > /etc/portage/package.mask"
    emerge -av qtile

Don't forget the config.py

.. code-block:: bash

    mkdir ~/.config/qtile
    cp build/lib/libqtile/resources/default_config.py ~/.config/qtile/config.py

Test Installation
-----------------

You can test your installation in Xephyr. If you don't have Xephyr you need to
set the kdrive USE-Flag for xorg-server

.. code-block:: bash

    echo "x11-base/xorg-server kdrive" >> /etc/portage/package.use

You can run Xephyr with

.. code-block:: bash

    Xephyr :1 -screen 800x600 -av -noreset

In another term you set DISPLAY to :1

.. code-block:: bash

    DISPLAY=:1

You start qtile simply with:

.. code-block:: bash

    qtile

*Contributed by Jonathan Sielhorst*
