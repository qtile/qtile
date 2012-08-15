Hacking Qtile
=============

Requirements
------------

* `Nose <http://nose.readthedocs.org/en/latest/>`_
* `Python X Library <http://python-xlib.sourceforge.net/>`_
* `Xephyr <http://www.freedesktop.org/wiki/Software/Xephyr>`_

Running the test suite
----------------------

.. code-block:: bash

   $ cd test
   $ nosetests

Using Xephyr and the test suite
-------------------------------

Qtile has a very extensive test suite, using the Xephyr nested X server. When
tests are run, a nested X server with a nested instance of Qtile is fired up,
and then tests interact with the Qtile instance through the client API. The
fact that we can do this is a great demonstration of just how completely
scriptable Qtile is. In fact, Qtile is designed expressly to be scriptable
enough to allow unit testing in a nested environment.

The Qtile repo includes a tiny helper script to let you quickly pull up a
nested instance instance of Qtile in Xephyr, using your current configuration.
Run it from the top-level of the repository, like this:

.. code-block:: bash

  ./scripts/xephyr

In practice, the development cycle looks something like this:

* make minor code change
* run appropriate test: ``nosetests --tests=test_module``
* GOTO 1, until hackage is complete
* run entire test suite: ``nosetests``
* commit

Resources
---------

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <http://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <http://standards.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <http://tronche.com/gui/x/xlib/>`_
