# How to contribute

Reporting bugs
--------------

Perhaps the easiest way to contribute to Qtile is to report any bugs you
run into on the [GitHub issue tracker](https://github.com/qtile/qtile/issues).

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

To give more information about your bug you can append logs from
`~/.local/share/qtile/qtile.log` or on occasionally events you can capture bugs
with `xtrace` for this have a deeper look on the documentation about
[capturing an xtrace](https://qtile.readthedocs.io/en/latest/manual/hacking.html#capturing-an-xtrace)

Writing code
============

To get started writing code for Qtile, check out our guide to [hacking](https://qtile.readthedocs.io/en/latest/manual/hacking.html).

Submit a pull request
---------------------

You've done your hacking and are ready to submit your patch to Qtile. Great!
Now it's time to submit a [pull request](https://help.github.com/articles/using-pull-requests)
to our [issue tracker](https://github.com/qtile/qtile/issues) on GitHub.

Pull requests are not considered complete until they include all of the
following:

1. Code: conforms to PEP8 and passes `make lint`.
2. Unit tests: CI tests pass. Please add new unit tests to ensure your code works and stays working.
   See [our website](http://docs.qtile.org/en/latest/manual/contributing.html#running-tests-locally)
   on how to run the tests locally.
3. Documentation: Should get updated if it needed.
4. A ``qtile migrate`` config migration is necessary for any config-breaking change.
5. Please do not include unrelated formatting changes.
6. Widgets don't need to catch their own exceptions, or introduce their own
   polling infrastructure. The code in ``libqtile.widget.base.*`` does all of
   this. Your widget should generally only include whatever parsing/rendering
   code is necessary, any other changes should go at the framework level.
7. Commit messages are more important that Github PR notes, since this is what
   people see when they are spelunking via ``git blame``. Please include all
   relevant detail in the actual git commit message (things like exact stack
   traces, copy/pastes of discussion in IRC/mailing lists, links to
   specifications or other API docs are all good).
8. PRs with multiple commits should not introduce code in one patch to then
   change it in a later patch. Please do a patch-by-patch review of your PR,
   and make sure each commit passes CI and makes logical sense on its own.

**Feel free to add your contribution (no matter how small) to the appropriate
place in the CHANGELOG as well!**

Thanks
