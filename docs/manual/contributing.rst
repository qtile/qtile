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

This section gives an overview about ``tox`` so that you don't have to search
`its documentation <https://tox.readthedocs.io/en/latest/>`_ just to get
started.

Checks are grouped in so-called ``environments``. Some of them are configured to
check that the code works (the usual unit test, e.g. ``py39``, ``pypy3``),
others make sure that your code conforms to the style guide (``pep8``,
``codestyle``, ``mypy``). A third kind of test verifies that the documentation
and packaging processes work (``docs``, ``docstyle``, ``packaging``).

We have configured ``tox`` to run the full suite of tests whenever a pull request
is submitted/updated. To reduce the amount of time taken by these tests, we have
created separate environments for both python versions and backends (e.g. tests for
x11 and wayland run in parallel for each python version that we currently support).

These environments were designed with automation in mind so there are separate
``test`` environments which should be used for running qtile's tests locally. By default,
tests will only run on x11 backend (but see below for information on how to set the
backend).

The following examples show how to run tests locally:
   * To run the functional tests, use ``tox -e test``. You can specify to only
     run a specific test file or even a specific test within that file with
     the following commands:

     .. code-block:: bash

        tox -e test # Run all tests in default python version
        tox -e test -- -x test/widgets/test_widgetbox.py  # run a single file
        tox -e test -- -x test/widgets/test_widgetbox.py::test_widgetbox_widget
        tox -e test -- --backend=wayland --backend=x11  # run tests on both backends
        tox -e test-both  # same as above 
        tox -e test-wayland  # Just run tests on wayland backend

   * To run style and building checks, use ``tox -e docs,packaging,pep8,...``.
     You can use ``-p auto`` to run the environments in parallel.

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

* `wlroots <https://gitlab.freedesktop.org/wlroots/wlroots>`_

  Pluggable, composable, unopinionated modules for building a Wayland compositor —
  or about 60,000 lines of code you were going to write anyway.

* `TinyWL <https://gitlab.freedesktop.org/wlroots/wlroots/-/tree/master/tinywl>`_

  A minimal Wayland compositor built with wlroots.
  Best starting point for learning wlroots by example.

* `DWL <https://codeberg.org/dwl/dwl>`_

  A compact, hackable Wayland compositor inspired by ``dwm``.
  Focused on minimalism and suckless philosophy, built on wlroots.

* `Sway <https://github.com/swaywm/sway>`_

  A tiling Wayland compositor and drop-in replacement for i3.
  Great example of a full-featured, mature compositor built on wlroots.

* `LabWC <https://github.com/labwc/labwc>`_

  A wlroots-based window-stacking compositor for Wayland, inspired by Openbox.

  It is light-weight and independent with a focus on simply stacking windows well and rendering some window decorations. 
  It takes a no-bling/frills approach and says no to features such as animations. 
  It relies on clients for panels, screenshots, wallpapers and so on to create a full desktop environment.

* `weston <https://gitlab.freedesktop.org/wayland/weston/-/tree/main/>`_

  The reference Wayland compositor. Overengineered for some, but shows "the correct way" to do things.

* `River <https://github.com/riverwm/river>`_

  A dynamic tiling Wayland compositor that's minimal, written in C and based on wlroots. Less bloated than sway, more experimental than dwl.

Articles & Documentation
----------------------------

* `Wayland Architecture Overview <https://wayland.freedesktop.org/architecture.html>`_ - Official architectural documentation
* `Protocol Extensions <https://wayland.app/>`_ - Interactive protocol browser and documentation
* `wlroots Documentation <https://gitlab.freedesktop.org/wlroots/wlroots/-/wikis/home>`_ - Official wlroots wiki and docs
* `The Wayland Book <https://wayland-book.com/>`_ — *A comprehensive introduction to Wayland and how it works.*
* `Introduction to Wayland <https://drewdevault.com/2017/06/10/Introduction-to-Wayland.html>`_ by Drew DeVault
* **Wayland Compositor Series by Drew DeVault:**

  * `Part 1: Hello wlroots <https://drewdevault.com/2018/02/17/Writing-a-Wayland-compositor-1.html>`_
  * `Part 2: Rigging up the server <https://drewdevault.com/2018/02/22/Writing-a-wayland-compositor-part-2.html>`_
  * `Part 3: Rendering a window <https://drewdevault.com/2018/02/28/Writing-a-wayland-compositor-part-3.html>`_

* `Input handling in wlroots <https://drewdevault.com/2018/07/17/Input-handling-in-wlroots.html>`_
* `Wayland Shells <https://drewdevault.com/2018/07/29/Wayland-shells.html>`_
* `Intro to Damage Tracking <https://emersion.fr/blog/2019/intro-to-damage-tracking/>`_ by emersion

Development Tools
--------------------

* `wayland-debug <https://gitlab.freedesktop.org/wayland/wayland/-/tree/main/debug>`_

  Debugging tool for inspecting Wayland protocol traffic. Invaluable for compositor/client debugging.

* `wayland-protocols <https://gitlab.freedesktop.org/wayland/wayland-protocols>`_

  Collection of extended Wayland protocols (xdg-shell, layer-shell, etc). Essential when implementing desktop-like behaviors.

* `wlr-protocols <https://gitlab.freedesktop.org/wlroots/wlr-protocols>`_

  Custom/proposed protocols used by wlroots-based compositors (e.g., for gamma control, foreign-toplevel, screencopy).

* `wf-recorder <https://github.com/ammen99/wf-recorder>`_

  Wayland screen recorder compatible with wlroots compositors. Great for demos and debugging output.

Libraries and Helpers
-------------------------

* `xwayland <https://gitlab.freedesktop.org/xorg/xserver/-/tree/master/hw/xwayland/>`_

  Lets X11 clients run inside a Wayland session. Needed for legacy app support in your compositor.

* `Pixman <https://www.pixman.org/>`_

  Low-level pixel manipulation library used by wlroots. Useful if you're doing custom rendering or damage handling.

* `Cairo <https://www.cairographics.org/>`_

  2D graphics library sometimes used for rendering surfaces in compositors or client UIs.

Video & Talks
----------------

* `Wayland Explained by Daniel Stone (FOSDEM) <https://www.youtube.com/watch?v=RIctzAQOe44>`_

  Excellent conceptual breakdown of Wayland internals from a veteran contributor.

* `Drew DeVault - Building Wayland desktop components with layer shell <https://www.youtube.com/watch?v=VuRXHJu5Kmg>`_

  Demonstration of the wlroots layer shell, examples of where it's useful from lead developer of `SwayWM <https://github.com/swaywm/sway>`_.

Reverse Engineering Examples
-------------------------------

* `wayland-utils <https://gitlab.freedesktop.org/wayland/wayland-utils>`_

  Includes tools like ``wayland-info`` that help inspect running compositors and protocols.

Related Projects & Alternatives
-----------------------------------

* `WLC <https://github.com/Cloudef/wlc>`_ (archived but insightful)

  Predecessor of wlroots — still interesting to read for historical and design insights.

* `Mir <https://github.com/MirServer/mir>`_

  Canonical's alternative Wayland compositor library — not wlroots-based but valuable for contrast.

* `Smithay <https://github.com/smithay/smithay>`_

  A compositor library in Rust, parallel to wlroots. Good if you want to understand differences in approach (e.g. memory safety).

Qtile-Specific Additions
----------------------------

* `qtile-wayland issues <https://github.com/qtile/qtile/issues?q=is%3Aissue+wayland>`_ - Current Wayland-related issues and discussions

Our Goal — C-based Qtile Wayland Backend
--------------------------------------------

* `Qtile WayC <https://github.com/qtile/qtile/tree/wayc>`_

  Ongoing effort to rewrite Qtile's Wayland backend in C using wlroots directly.

  **Why?**

  * Wlroots changes → requires tracking upstream C changes
  * Updating ``pywlroots`` for new APIs
  * Translating C API semantics into Python
  * Then updating Qtile to match those changes

  Doing it in C cuts through all that indirection and brings more control.

* `Join Wayland development discussion on Discord <https://discord.com/channels/955163559086665728/1383006376695173230>`_
