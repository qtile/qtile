================
Developing Qtile
================

Using Xephyr and the test suite
===============================

Qtile has a very extensive test suite, using the Xephyr nested X server. When
tests are run, a nested X server with a nested instance of Qtile is fired up,
and then tests interact with the Qtile instance through the client API. The
fact that we can do this is a great demonstration of just how completely
scriptable Qtile is. In fact, Qtile is designed expressly to be scriptable
enough to allow unit testing in a nested environment.

The Qtile repo includes a tiny helper script to let you quickly pull up a
nested instance instance of Qtile in Xephyr, using your current configuration.
Run it from the top-level of the repository, like this::

  ./test/scripts/xephyr                      

In practice, the development cycle looks something like this:

#.  Make minor code change
#.  Run appropriate tests using ``nosetests``
#.  GOTO 1, until hackage is complete
#.  Run entire test suite 
#.  Commit                   


Resources
=========

Here are a number of resources that may come in handy:


* `Inter-Client Conventions Manual`_
* `Extended Window Manager Hints`_
* A reasonable basic `Xlib Manual`_

.. _Inter-Client Conventions Manual: http://tronche.com/gui/x/icccm/
..  _Extended Window Manager Hints: http://standards.freedesktop.org/wm-spec/wm-spec-latest.html
.. _Xlib Manual: http://tronche.com/gui/x/xlib/

