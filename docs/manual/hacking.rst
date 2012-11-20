Hacking Qtile
=============

Requirements
------------

Any reasonably recent version of these should work, so you can probably just
install them from your package manager.

* `Nose <http://nose.readthedocs.org/en/latest/>`_
* `Python X Library <http://python-xlib.sourceforge.net/>`_
* `Xephyr <http://www.freedesktop.org/wiki/Software/Xephyr>`_

Running the test suite
----------------------

.. code-block:: bash

   $ cd test
   $ nosetests

Note: nose runs the tests against the first version of qtile it finds on your
``$PYTHONPATH``; for most people this is the currently installed version of
qtile.

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

Second X Session
----------------

Some users prefer to test Qtile in it's own brand new X session. If you'd like
to run a second X session, you can switch to a new tty and start a new one
with ``xinit second_xsession``, where ``second_xsession`` is a file invoking
your development version of qtile (and doing any other setup you want).
Examples of custom ``xsession`` files are available in `qtile-examples
<https://github.com/qtile/qtile-examples>`_.

Contributing to Qtile
---------------------

Now you've got a patch you want to submit to be merged to Qtile. Typically,
this is done via github `pull requests
<https://help.github.com/articles/using-pull-requests>`_. Qtile uses a `well
known <http://nvie.com/posts/a-successful-git-branching-model/>`_ branching
model; master is our current release, and the ``develop`` branch is what all
pull requests should be based against.

While not all of our code follows `PEP8
<http://www.python.org/dev/peps/pep-0008/>`_, we do try to adhere to it where
possible, and ideally any new code would be PEP8 compliant. Perhaps the
biggest issue is tabs vs. spaces: only 4 space tabs, please.

Feel free to add your contribution (no matter how small) to the appropriate
place in the CHANGELOG as well!

Reporting Bugs
--------------

Please report any bugs you find to the `github issue tracker
<https://github.com/qtile/qtile/issues>`_.

Resources
---------

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <http://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <http://standards.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <http://tronche.com/gui/x/xlib/>`_
