============
Contributing
============

.. _reporting:

Reporting bugs
==============

Perhaps the easiest way to contribute to Qtile is to report any bugs you
run into on the `GitHub issue tracker <https://github.com/qtile/qtile/issues>`_.

Useful bug reports are ones that get bugs fixed. A useful bug report normally
has two qualities:

1. **Reproducible.** If your bug is not reproducible it will never get fixed.
   You should clearly mention the steps to reproduce the bug. Do not assume or
   skip any reproducing step. Describe the issue, step-by-step, so that it is
   easy to reproduce and fix.

2. **Specific.** Do not write an essay about the problem. Be specific and to the
   point. Try to summarize the problem in a succinct manner. Do not combine multiple problems even if they seem to be similar. Write
   different reports for each problem.

Ensure to include any appropriate log entries from
``~/.local/share/qtile/qtile.log`` and/or ``~/.xsession-errors``!
Sometimes, an ``xtrace`` is requested. If that is the case, refer to
:ref:`capturing an xtrace <capturing-an-xtrace>`.


Writing code
============

To get started writing code for Qtile, check out our guide to :ref:`hacking`.
A more detailed page on creating widgets is available :ref:`here <widget-creation>`.

.. important::

    Use a separate **git branch** to make rebasing easy. Ideally, you would
    ``git checkout -b <my_feature_branch_name>`` before starting your work.

    See also: :ref:`using git <using-git>`.

.. _submitting-a-pr:

Submit a pull request
---------------------

You've done your hacking and are ready to submit your patch to Qtile. Great!
Now it's time to submit a
`pull request <https://help.github.com/articles/using-pull-requests>`_
to our `issue tracker <https://github.com/qtile/qtile/issues>`_ on GitHub.

.. important::

    Pull requests are not considered complete until they include all of the
    following:

    * **Code** that conforms to PEP8 and is formatted by `black
      <https://black.readthedocs.io>`_.
    * **Unit tests** that pass locally and in our CI environment (More below).
      *Please add unit tests* to ensure that your code works and stays working!
    * **Documentation** updates on an as needed basis.
    * A ``qtile migrate`` **migration** is required for config-breaking changes.
      See `migrate.py <https://github.com/qtile/qtile/blob/libqtile/scripts/migrate.py>`_
      for examples and consult the `bowler documentation <https://pybowler.io>`_
      for detailed help and documentation.
    * **Code** that does not include *unrelated changes*. Examples for this are
      formatting changes, replacing quotes or whitespace in other parts of the
      code or "fixing" linter warnings popping up in your editor on existing
      code. *Do not include anything like the above!*
    * **Widgets** don't need to catch their own exceptions, or introduce their
      own polling infrastructure. The code in ``libqtile.widget.base.*`` does
      all of this. Your widget should generally only include whatever
      parsing/rendering code is necessary, any other changes should go at the
      framework level. Make sure to double-check that you are not
      re-implementing parts of ``libqtile.widget.base``.
    * **Commit messages** are more important that Github PR notes, since this is
      what people see when they are spelunking via ``git blame``. Please include
      all relevant detail in the actual git commit message (things like exact
      stack traces, copy/pastes of discussion in IRC/mailing lists, links to
      specifications or other API docs are all good). If your PR fixes a Github
      issue, it might also be wise to link to it with ``#1234`` in the commit
      message.
    * PRs with **multiple commits** should not introduce code in one patch to
      then change it in a later patch. Please do a patch-by-patch review of your
      PR, and make sure each commit passes CI and makes logical sense on its
      own. In other words: *do* introduce your feature in one commit and maybe
      add the tests and documentation in a seperate commit. *Don't* push commits
      that partially implement a feature and are basically broken.

.. note:: Others might ban *force-pushes*, we allow them and prefer them over
   incomplete commits or commits that have a bad and meaningless commit
   description.

Feel free to add your contribution (no matter how small) to the appropriate
place in the CHANGELOG as well!

.. _unit-testing:

Unit testing
------------

We must test each *unit* of code to ensure that new changes to the code do not
break existing functionality. The framework we use to test Qtile is `pytest
<https://docs.pytest.org>`_. How pytest works is outside of the scope of this
documentation, but there are tutorials online that explain how it is used.

Our tests are written inside the ``test`` folder at the top level of the
repository. Reading through these, you can get a feel for the approach we take
to test a given unit. Most of the tests involve an object called ``manager``.
This is the test manager (defined in test/helpers.py), which exposes a command
client at ``manager.c`` that we use to test a Qtile instance running in a
separate thread as if we were using a command client from within a running
Qtile session.

For any Qtile-specific question on testing, feel free to ask on our `issue
tracker <https://github.com/qtile/qtile/issues>`_ or on IRC (#qtile on
irc.oftc.net).

.. _running-tests-locally:

Running tests locally
---------------------

This section gives an overview about ``tox`` so that you don't have to search
`its documentation <https://tox.readthedocs.io/en/latest/>`_ just to get
started.
Checks are grouped in so-called ``environments``. Some of them are configured to
check that the code works (the usual unit test, e.g. ``py39``, ``pypy3``),
others make sure that your code conforms to the style guide (``pep8``,
``codestyle``, ``mypy``). A third kind of test verifies that the documentation
and packaging processes work (``docs``, ``docstyle``, ``packaging``).

The following examples show how to run tests locally:
   * To run the functional tests, use ``tox -e py39`` (or a different
     environment). You can specify to only run a specific test file or even a
     specific test within that file with the following commands:

     .. code-block:: bash

        tox -e py39 # Run all tests with python 3.9 as the interpreter
        tox -e py39 -- -x test/widgets/test_widgetbox.py  # run a single file
        tox -e py39 -- -x test/widgets/test_widgetbox.py::test_widgetbox_widget

   * To run style and building checks, use ``tox -e docs,packaging,pep8,...``.
     You can use ``-p auto`` to run the environments in parallel.

     .. important::

        The CI is configured to run all the environments. Hence it can be time-
        consuming to make all the tests pass. As stated above, pull requests
        that don't pass the tests are considered incomplete. Don't forget that
        this does not only include the functionality, but the style, typing
        annotations (if necessary) and documentation as well!
