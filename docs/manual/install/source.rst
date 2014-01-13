Installing from Source
======================

Qtile relies on some cutting-edge features in PyCairo, XCB, and xpyb. Until the
latest versions of these projects make it into distros, it's best to use recent
checkouts from their repositories. You'll need python's ``setuptools``
installed. Here's a brief step-by-step guide:


libxcb
------

.. code-block:: bash

    git clone git://anongit.freedesktop.org/git/xcb/libxcb
    cd libxcb
    ./autogen.sh
    make
    sudo make install


xpyb
-------

Either ``xpyb-ng`` or ``xpyb`` versions >= 1.3.1 should work. The ``xpyb``
build itself has historically had some package config issues, so we provide
xpyb-ng for people who want to use setuptools. (The implementations are also
slightly different, but users have reported that qtile is stable on either
fork.) For users with a system version of ``xcb-proto`` < 1.7, xpyb will not
build correctly (you get an ``AttributeError: 'ListType' object has no
attribute 'parent'``). However, xpyb-ng provides a branch called
``pre-1.7-xproto`` which has a hack to fix this issue.

.. code-block:: bash

    git clone git://anongit.freedesktop.org/xcb/xpyb
    cd xpyb && ./autogen.sh
    ./configure
    make install

.. code-block:: bash

    git clone git@github.com:tych0/xpyb-ng.git
    cd xpyb-ng
    python setup.py install


cairo
-----

The latest cairo release works, but recompiling with xcb support is needed.

.. code-block:: bash

    wget http://cairographics.org/releases/cairo-1.10.0.tar.gz
    tar xvzf cairo-1.10.0.tar.gz
    cd cairo-1.10.0
    ./autogen.sh --enable-xcb
    make
    sudo make install


py2cairo
--------

.. code-block:: bash

    git clone git://git.cairographics.org/git/py2cairo
    cd py2cairo
    ./autogen.sh --enable-xcb

Check the configure output to make sure that XPYB is correctly detected.

.. code-block:: bash

    make
    sudo make install


PyGTK
-----

We also require a reasonably recent version of the Python GTK bindings, in
particular, the pango module. You should just be able to install this using
your chosen distribution's package manager.

Qtile
-----

.. code-block:: bash

    git clone git://github.com/qtile/qtile.git
    cd qtile
    sudo python setup.py install
