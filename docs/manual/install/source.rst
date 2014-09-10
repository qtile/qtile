Installing from Source
======================

Qtile itself is very easy to install, you'll just need python's ``setuptools``.
Additionally, qtile uses a branch of cairocffi that has not yet been merged, so
you need to install that from source. A step by step guide is below.

xcffib
------

Qtile uses xcffib_ as an XCB binding, which has its own instructions for
building from source including building several Haskell packages, but is
available from PyPi via:

.. code-block:: bash

    sudo pip install xcffib

.. _xcffib: https://github.com/tych0/xcffib

cairocffi
---------

You'll need to install a source branch of cairocffi_, since the xcffib patches
are not yet merged. Thankfully, pip makes this fairly easy:

.. code-block:: bash

    sudo pip install git://github.com/flacjacket/cairocffi.git@xcb

.. _cairocffi: https://pythonhosted.org/cairocffi/overview.html

asyncio/trollius
----------------

Qtile uses the asyncio module as introduced in `PEP 3156`_ for its event loop.
Based on your Python version, there are different ways to install this:

- Python >=3.4: The `asyncio module`_ comes as part of the standard library, so
  there is nothing more to install.
- Python 3.3: This has all the infastructure needed to implement PEP 3156, but
  the asyncio module must be installed from the `Tulip project`_.  This is done
  by calling:

  .. code-block:: bash
    
      sudo pip install asyncio

  Alternatively, you can install trollius (see next point).
- Python 2 and <=3.2 (and 3.3 without asyncio): You will need to install
  trollius_, which backports the asyncio module functionality to work without
  the infastructure introduced in PEP 3156.  You can install this from PyPi:

  .. code-block:: bash

      sudo pip install trollius

.. _PEP 3156: http://python.org/dev/peps/pep-3156/
.. _asyncio module: https://docs.python.org/3/library/asyncio.html
.. _Tulip project: https://code.google.com/p/tulip/
.. _trollius: http://trollius.readthedocs.org/

Qtile
-----

With the dependencies in place, you can now install qtile:

.. code-block:: bash

    git clone git://github.com/qtile/qtile.git
    cd qtile
    sudo python setup.py install
