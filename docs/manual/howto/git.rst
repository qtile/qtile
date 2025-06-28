.. _using-git:

=============
Using ``git``
=============

``git`` is the version control system that is used to manage all of the source
code. It is very powerful, but might be frightening at first.
This page should give you a quick overview, but for a complete guide you will
have to search the web on your own.
Another great resource to get started practically without having to try out the
newly-learned commands on a pre-existing repository is
`learn git branching <https://learngitbranching.js.org>`_.
You should probably learn the basic ``git`` vocabulary and then come back to
find out how you can use all that practically. This guide will be oriented on
how to create a pull request and things might be in a different order compared
to the introductory guides.

.. warning:: This guide is not complete and never will be. If something isn't
   clear, consult other sources until you are confident you know what you are
   doing.

I want to try out a feature somebody is working on
==================================================
If you see a pull request on `GitHub <https://www.github.com/qtile/qtile/pulls>`_
that you want to try out, have a look at the line where it says::

  user wants to merge n commits into qtile:master from user:branch

Right now you probably have one *remote* from which you can fetch changes, the
``origin``. If you cloned ``qtile/qtile``, ``git remote show origin`` will spit
out the *upstream* url. If you cloned your fork, ``origin`` points to it and you
probably want to ``git remote add upstream https://www.github.com/qtile/qtile``.
To try out somebody's work, you can add their fork as a new remote::

  git remote add <user> https://www.github.com/user/qtile

where you fill in the username from the line we asked you to search for before.
Then you can load data from that remote with ``git fetch`` and then ultimately
check out the branch with ``git checkout <user>/<branch>``.

**Alternatively**, it is also possible to fetch and checkout pull requests
without needing to add other remotes. The upstream remote is sufficient::

  git fetch upstream pull/<id>/head:pr<id>
  git checkout pr<id>

The numeric pull request id can be found in the url or next to the title
(preceeded by a # symbol).

.. note:: Having the feature branch checked out doesn't mean that it is
   installed and will be loaded when you restart qtile. You might still need to
   install it with ``uv``.

I committed changes and the tests failed
========================================

You can easily change your last commit: After you have done your work,
``git add`` everything you need and use ``git commit --amend`` to change your
last commit. This causes the git history of your local clone to be diverged from
your fork on GitHub, so you need to force-push your changes with::

  git push -f <origin> <feature-branch>

where origin might be your user name or ``origin`` if you cloned your fork and
feature-branch is to be replaced by the name of the branch you are working on.

Assuming the feature branch is currently checked out, you can usually omit it
and just specify the origin.

I was told to rebase my work
============================

If *upstream/master* is changed and you happened to change the same files as the
commits that were added upstream, you should rebase your work onto the most
recent *upstream/master*. Checkout your master, pull from *upstream*, checkout
your branch again and then rebase it::

  git checkout master
  git pull upstream/master
  git checkout <feature-branch>
  git rebase upstream/master

You will be asked to solve conflicts where your diff cannot be applied with
confidence to the work that was pushed upstream. If that is the case, open the
files in your text editor and resolve the conflicts manually. You possibly need
to ``git rebase --continue`` after you have resolved conflicts for one commit if
you are rebasing multiple commits.

Note that the above doesn't work if you didn't create a branch. In that case you
will find guides elsewhere to fix this problem, ideally by creating a branch and
resetting your master branch to where it should be.

I was told to squash some commits
=================================

If you introduce changes in one commit and replace them in another, you are told
to squash these changes into one single commit without the intermediate step::

  git rebase -i master

opens a text editor with your commits and a comment block reminding you what you
can do with your commits. You can reword them to change the commit message,
reorder them or choose ``fixup`` to squash the changes of a commit into the
commit on the line above.

This also changes your git history and you will need to force-push your changes
afterwards.

Note that interactive rebasing also allows you to split, reorder and edit
commits.

I was told to edit a commit message
===================================

If you need to edit the commit message of the last commit you did, use::

  git commit --amend

to open an editor giving you the possibility to reword the message. If you want
to reword the message of an older commit or multiple commits, use
``git rebase -i`` as above with the ``reword`` command in the editor.


.. toctree::
    :maxdepth: 1

    Releasing <../releasing>
