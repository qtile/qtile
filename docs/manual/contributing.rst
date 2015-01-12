============
Contributing
============

Reporting bugs
==============

Perhaps the easiest way to contribute to Qtile is to report any bugs you
run into on the `github issue tracker <https://github.com/qtile/qtile/issues>`_.

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

Writing code
============

To get started writing code for Qtile, check out our guide to :doc:`hacking`.

Git workflow
------------

Our workflow is based on Vincent Driessen's `successful git branching model
<http://nvie.com/posts/a-successful-git-branching-model/>`_:

* The ``master`` branch is our current release
* The ``develop`` branch is what all pull requests should be based against
* Feature branches, generally named ``feature/branch-name``, are where new
  features, both major and minor, should be developed.

.. seqdiag:: /_static/diagrams/git-branching-strategy.diag

`git-flow <https://github.com/nvie/gitflow>`_ is a git plugin that helps
facilitate this branching strategy. It's not required, but can help make
things a bit easier to manage. There is also a good write up on
`using git-flow <http://jeffkreeftmeijer.com/2010/why-arent-you-using-git-flow/>`_.

We also request that git commit messages follow the
`standard format <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

Submit a pull request
---------------------

You've done your hacking and are ready to submit your patch to Qtile. Great!
Now it's time to submit a
`pull request <https://help.github.com/articles/using-pull-requests>`_
to our `issue tracker <https://github.com/qtile/qtile/issues>`_ on Github.

.. important::

    Pull requests are not considered complete until they include all of the
    following:

    * **Code** that conforms to PEP8.
    * **Unit tests** that pass locally and in our CI environment. [#f1]_
    * **Documentation** updates on an as needed basis.

Feel free to add your contribution (no matter how small) to the appropriate
place in the CHANGELOG as well!

.. [#f1] Qtile's tests are not particularly robust under load, so travis-ci
    will sometimes fail tests that would otherwise pass. We are working to fix
    this, but in the meantime, if your tests pass locally but not when you make a
    PR, don't fret, just ask someone on IRC or the mailing list to take a look to
    make sure it is a known issue.
