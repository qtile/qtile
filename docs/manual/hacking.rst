Hacking Qtile
=============

Requirements
------------

If you plan to run the test suite, you will need `the Pry unit testing
framework <https://github.com/cortesi/pry>`_, and the `Python X Library
<http://python-xlib.sourceforge.net/>`_.

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

::

  ./scripts/xephyr

In practice, the development cyclce looks something like this:

* make minor code change
* run appropriate test: ``pry ./test_module.uMySuite``
* GOTO 1, until hackage is complete
* run entire test suite: ``pry``
* commit

Resources
---------

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <http://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <http://standards.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <http://tronche.com/gui/x/xlib/>`_
