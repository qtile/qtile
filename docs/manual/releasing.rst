===============
Releasing Qtile
===============

Here is a short document about how to tag Qtile releases.

1. create a "Release vX.XX.XX" commit. I like to thank all the contributors; I
   find that list with something like:

.. code-block:: bash

   git log --oneline --no-merges --format=%an $(git describe --tags --abbrev=0)..HEAD | sort -u

note that this can sometimes generate duplicates if people commit with slightly
different names; I typically clean it up manually.

Be sure that you GPG-sign (i.e. the ``-S`` argument to ``git commit``) this commit.

2. Create a GPG-signed annotated tag (``git tag -a -s vX.XX.XX``); I usually just use
   exactly the same commit message as the actual release commit above.

3. Push your tag to qtile/qtile directly:

.. code-block:: bash

   git push origin vX.XX.XX

4. Check the `Release action
   <https://github.com/qtile/qtile/actions/workflows/release.yml>`_; the "Test
   PyPI upload" action should build and upload the wheels to the test
   environment. If this step breaks, you can delete your tag (``git push ...
   :vX.XX.XX``), fix the bug, re-tag, and hopefully that will work.

5. Create a new `Github release
   <https://github.com/qtile/qtile/releases/new>`_; this is what will trigger
   the actions in ``.github/workflows/release.yml`` to actually do the real pypi
   upload.

6. Make sure all of these actions complete as green. The release should show up
   in a few minutes after completion here: https://pypi.org/project/qtile/

7. Push your tag commit to master.

8. Update `the release string
   <https://github.com/qtile/qtile.org/blob/master/config.toml#L49>`_ on
   qtile.org.

8. Relax and enjoy a $beverage. Thanks for releasing!
