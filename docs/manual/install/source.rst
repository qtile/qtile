Installing from Source
======================

Qtile itself is very easy to install, you'll just need python's ``setuptools``.
Additionally, qtile uses a branch of cairocffi that has not yet been merged, so
you need to install that from source. A step by step guide is below.

cffi
----

Any version of cffi >= 0.8.2 should work. `cffi
<https://bitbucket.org/cffi/cffi>`_'s source has installation instructions, or
you can install it from pypi:

.. code-block:: bash

    sudo pip install cffi

xcffib
------

Qtile depends on `xcffib <https://github.com/tych0/xcffib>`_, which is
has its own instructions for building from source, or is available from pypi
via:

.. code-block:: bash

    sudo pip install xcffib


cairocffi
---------

You'll need to build a source branch of cairocffi, since the xcffib patches are
not yet merged. Thankfully, this is fairly easy:

.. code-block:: bash

    git clone -b xcb https://github.com/flacjacket/cairocffi.git
    cd cairocffi && sudo python setup.py install

python-gobject
--------------

We also require a reasonably recent version of the Python gobject bindings. You
should just be able to install this using your chosen distribution's package
manager.

Qtile
-----

.. code-block:: bash

    git clone git://github.com/qtile/qtile.git
    cd qtile
    sudo python setup.py install
