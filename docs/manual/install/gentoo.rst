Installing on Gentoo
====================

Dependencies
------------

libxcb
~~~~~~

Take libxcb-1.8.1 from portage.
You need to unmask.

.. code-block:: bash

    echo "x11-libs/libxcb ~amd64" >> /etc/portage/package.keywords
    emerge -av libxcb


xpyb
~~~~

Take xpyb-1.3.1 from portage.
You need to unmask it.

.. code-block:: bash

    echo "x11-libs/xpyb ~amd64" >> /etc/portage/package.keywords
    emerge -av xpyb


cairo
~~~~~

Take cairo-1.10.2-r2 from portage.
It worked for me with these USE-Flags:  X, glib, opengl, svg and xcb.
And you need to unmask it.

.. code-block:: bash

    echo "x11-libs/cairo ~amd64" >> /etc/portage/package.keywords
    echo "x11-libs/cairo X glib opengl svg xcb" >> /etc/portage/package.use
    emerge -av x11-libs/cairo


py2cairo
~~~~~~~~

.. code-block:: bash

    git clone git://git.cairographics.org/git/py2cairo
    cd py2cairo
    ./configure --prefix=/usr
    make
    sudo make install

It's also possible (and recommended) to put this into a virtualenv.

.. code-block:: bash

    ./configure --prefix=/path/to/virtualenv 


pygtk
~~~~~

Take pygtk-2.24.0-r2 from portage:

.. code-block:: bash

    emerge -av pygtk

qtile
~~~~~

.. code-block:: bash

    git clone git://github.com/qtile/qtile
    cd qtile
    sudo python setup.py install --record files_uninstall.txt

Don't forget the config.py

.. code-block:: bash

    mkdir ~/.config/qtile
    cp build/lib/libqtile/resources/default-config.py ~/.config/qtile/config.py

Annotation
----------

* xpyb-ng from https://github.com/qtile/xpyb-ng installs with setup.py.
  I had to put the xpyb.h and xpyb.pc manualy to /usr/include/python2.7
  and /usr/lib64/pkgconfig/. You also have to edit xpyb.pc for the right
  prefix.
  There will maybe less errors.
* pycairo in portage gets installed without xpyb support. Maybe, cause
  they use waf for intallation. But i'm quiet new to python so i can't
  say.
* For pycairo need to specify ./autogen.sh --enable-xcb otherwise you 
  will get the dreaded TypeError: pycairo was not compiled with xpyb 
  support error

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

----

Ebuild
------

**TODO** -- An ebuild package is available from the Funtoo project. We need
testers to verify that this works.

https://github.com/funtoo/portage/blob/75b2dd1755081c7dc09bca275e93426c886d0f75/x11-wm/qtile/qtile-9999.ebuild
