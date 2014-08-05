Hacking Qtile
=============

Requirements
------------

Any reasonably recent version of these should work, so you can probably just
install them from your package manager.

* `Nose <http://nose.readthedocs.org/en/latest/>`_
* `Xephyr <http://www.freedesktop.org/wiki/Software/Xephyr>`_
* ``xeyes`` and ``xclock``

On ubuntu, this can be done with ``sudo apt-get install python-nose
xserver-xephyr x11-apps``.

Using Xephyr and the test suite
-------------------------------

Qtile has a very extensive test suite, using the Xephyr nested X server. When
tests are run, a nested X server with a nested instance of Qtile is fired up,
and then tests interact with the Qtile instance through the client API. The
fact that we can do this is a great demonstration of just how completely
scriptable Qtile is. In fact, Qtile is designed expressly to be scriptable
enough to allow unit testing in a nested environment.

The Qtile repo includes a tiny helper script to let you quickly pull up a
nested instance of Qtile in Xephyr, using your current configuration.
Run it from the top-level of the repository, like this:

.. code-block:: bash

  ./scripts/xephyr

In practice, the development cycle looks something like this:

1. make minor code change
#. run appropriate test: ``nosetests --tests=test_module``
#. GOTO 1, until hackage is complete
#. run entire test suite: ``nosetests``
#. commit

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

Now you've got a patch you want to submit to be merged to Qtile! Typically,
this is done via github `pull requests
<https://help.github.com/articles/using-pull-requests>`_. Qtile uses a `well
known <http://nvie.com/posts/a-successful-git-branching-model/>`_ branching
model; master is our current release, and the ``develop`` branch is what all
pull requests should be based against.

While not all of our code follows `PEP8
<http://www.python.org/dev/peps/pep-0008/>`_, we do try to adhere to it where
possible, and ideally any new code would be PEP8 compliant. ``make lint`` will
run a linter with our configuration over libqtile to ensure your patch complies
with reasonable formatting constraints. We also request that git commit
messages follow the `standard format
<http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

All pull requests for widgets should come with associated documentation.
Additionally, all widgets should use our defaults system (see
`libqtile/widget/clock.py
<https://github.com/qtile/qtile/blob/develop/libqtile/widget/clock.py>`_ for an
example); this will allow us to autogenerate the documentation in the future.
Finally, when a widget API is changed, you should deprecate the change using
``libqtile.widget.base.deprecated`` to warn users, in additon to adding it to
the appropriate place in the changelog. We will typically remove deprecated
APIs one tag after they are deprecated.

Of course, your patches should also pass the unit tests as well (i.e. ``make
check``). Qtile's tests are not particularly robust under load, so travis-ci
will sometimes fail tests that would otherwise pass. We are working to fix
this, but in the meantime, if your tests pass locally but not when you make a
PR, don't fret, just ask someone on IRC or the mailing list to take a look to
make sure it is a known issue.

Please add your contribution (no matter how small) to the appropriate place in
the CHANGELOG as well!

Resources
---------

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <http://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <http://standards.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <http://tronche.com/gui/x/xlib/>`_
