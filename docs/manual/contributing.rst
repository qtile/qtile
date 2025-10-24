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

    * **Code** that conforms to our linters and formatters.
      Run ``pre-commit install`` to install pre-commit hooks that will
      make sure your code is compliant before any commit.
    * **Unit tests** that pass locally and in our CI environment (More below).
      *Please add unit tests* to ensure that your code works and stays working!
    * **Documentation** updates on an as needed basis.
    * A ``qtile migrate`` **migration** is required for config-breaking changes.
      See :doc:`here <commands/shell/qtile-migrate>` 
      for current migrations and see below for further information.
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

You can run our various CI bits locally with:

.. code-block:: bash

    make lint  # to run the pre-commit checks
    make check  # to run both backends for the minimum python version
    make QTILE_CI_PYTHON=3.13 QTILE_CI_BACKEND=x11  # to run a specific backend/python version combination
    uv run --python=3.13 pytest --backend=wayland ./test/widgets/test_widgetbox.py::test_widgetbox_widget # to run a specific test

See ``.github/workflows/ci.yml`` for the full matrix of supported
python+backend versions. All of these will matter, but for most changes it is
only necessary to run one set locally to confirm the change is correct.

.. important::

    The CI is configured to run all the environments. Hence it can be time-
    consuming to make all the tests pass. As stated above, pull requests
    that don't pass the tests are considered incomplete. Don't forget that
    this does not only include the functionality, but the style, typing
    annotations (if necessary) and documentation as well!

Writing migrations
------------------

Migrations are needed when a commit introduces a change which makes a breaking change to
a user's config. Examples include renaming classes, methods, arguments and moving modules or
class definitions.

Where these changes are made, it is strongly encouraged to support the old syntax where possible
and warn the user about the deprecations.

Whether or not a deprecation warning is provided, a migration script should be provided that will
modify the user's config when they run ``qtile migrate``.

Click here for detailed instructions on :doc:`how-to-migrate`.

.. toctree::
    :maxdepth: 1
    :hidden:

    how-to-migrate

Deprecation Policy
------------------

Interfaces that have been deprecated for at least two years after the first
release containing the deprecation notice can be deleted. Since all new
breaking changes should have a migration, users can use ``qtile migrate`` to
bootstrap across versions when migrations are deleted if necessary.

Deprecated interfaces that do not have a migration (i.e. whose deprecation was
noted before the migration feature was introduced) are all fair game to be
deleted, since the migration feature is more than two years old.

.. _wayland_contribution:

Recommended Resources for Getting Started with Wayland Development
===================================================================

Source Code Repositories
----------------------------

The following are some repositories with useful Wayland source code:

* `wlroots <https://gitlab.freedesktop.org/wlroots/wlroots>`_

  The Wayland library we use. Useful documentation is in header files.

* `TinyWL <https://gitlab.freedesktop.org/wlroots/wlroots/-/tree/master/tinywl>`_

  A minimal Wayland compositor built with Wlroots.

* `DWL <https://codeberg.org/dwl/dwl>`_

  A compact, hackable Wayland compositor inspired by ``dwm``.

* `Sway <https://github.com/swaywm/sway>`_

  A tiling Wayland compositor and drop-in replacement for i3.

* `LabWC <https://github.com/labwc/labwc>`_

  A wlroots-based window-stacking compositor for Wayland, inspired by Openbox.

* `weston <https://gitlab.freedesktop.org/wayland/weston/-/tree/main/>`_

  The reference Wayland compositor.

* `River <https://github.com/riverwm/river>`_

  A dynamic tiling Wayland compositor written in Zig.

Articles & Documentation
----------------------------

* `The Wayland Book <https://wayland-book.com/>`_ - An introduction to Wayland
* `Wayland Architecture Overview <https://wayland.freedesktop.org/architecture.html>`_ - Wayland architecture
* `Protocol Extensions <https://wayland.app/>`_ - Interactive protocol browser and documentation
* `wlroots Documentation <https://wlroots.pages.freedesktop.org/wlroots/>`_ - Wlroots header file docs as HTML

Some outdated/old resources but that still are useful:
* `Introduction to Wayland <https://drewdevault.com/2017/06/10/Introduction-to-Wayland.html>`_ by Drew DeVault
* **Wayland Compositor Series by Drew DeVault:**

  * `Part 1: Hello wlroots <https://drewdevault.com/2018/02/17/Writing-a-Wayland-compositor-1.html>`_
  * `Part 2: Rigging up the server <https://drewdevault.com/2018/02/22/Writing-a-wayland-compositor-part-2.html>`_
  * `Part 3: Rendering a window <https://drewdevault.com/2018/02/28/Writing-a-wayland-compositor-part-3.html>`_

* `Input handling in wlroots <https://drewdevault.com/2018/07/17/Input-handling-in-wlroots.html>`_
* `Wayland Shells <https://drewdevault.com/2018/07/29/Wayland-shells.html>`_
* `Intro to Damage Tracking <https://emersion.fr/blog/2019/intro-to-damage-tracking/>`_ by emersion

Video & Talks
----------------

* `Wayland Explained by Daniel Stone (FOSDEM) <https://www.youtube.com/watch?v=RIctzAQOe44>`_

* `Drew DeVault - Building Wayland desktop components with layer shell <https://www.youtube.com/watch?v=VuRXHJu5Kmg>`_
