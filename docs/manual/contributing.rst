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
   skip any reproducing step. Described the issue, step-by-step, so that it is
   easy to reproduce and fix.

2. **Specific.** Do not write a essay about the problem. Be Specific and to the
   point. Try to summarize the problem in minimum words yet in effective way.
   Do not combine multiple problems even they seem to be similar. Write
   different reports for each problem.

Ensure to include any appropriate log entries from
``~/.local/share/qtile/qtile.log`` and/or ``~/.xsession-errors``!

Writing code
============

To get started writing code for Qtile, check out our guide to :ref:`hacking`.

A more detailed page on creating widgets is available :ref:`here <widget-creation>`.

Submit a pull request
---------------------

You've done your hacking and are ready to submit your patch to Qtile. Great!
Now it's time to submit a
`pull request <https://help.github.com/articles/using-pull-requests>`_
to our `issue tracker <https://github.com/qtile/qtile/issues>`_ on GitHub.

.. important::

    Pull requests are not considered complete until they include all of the
    following:

    * **Code** that conforms to PEP8.
    * **Unit tests** that pass locally and in our CI environment (More below).
    * **Documentation** updates on an as needed basis.

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
This is the test manager (defined in test/conftest.py), which exposes a command
client at ``manager.c`` that we use to test a Qtile instance running in a
separate thread as if we were using a command client from within a running
Qtile session.

For any Qtile-specific question on testing, feel free to ask on our `issue
tracker <https://github.com/qtile/qtile/issues>`_ or on IRC (#qtile on
irc.oftc.net).
