========================
Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as:

- `qtile`_ stable branch(release) of qtile.
- `qtile-python3-git`_ development branch of qtile.

Using an AUR Helper
===================

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use yaourt:

.. code-block:: bash

    # for release
    yaourt -S qtile
    # or for develop
    yaourt -S qtile-python3-git

Using makepkg
=============

The latest version of either package can be obtained by downloading a snapshot
or cloning its repository:

.. code-block:: bash

    # snapshot
    curl -s https://aur.archlinux.org/cgit/aur.git/snapshot/<package-name>.tar.gz | tar -xvzf -
    # or repository
    git clone https://aur.archlinux.org/<package-name>.git

Next makepkg has to be called in the directory where the files were saved. It
installs missing dependencies using pacman, builds the package, installs it
and removes obsolete build-time dependencies afterwards:

.. code-block:: bash

    cd <package-name>
    makepkg -sri

Please see the Arch Wiki for more information on installing packages from
the AUR:
https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages

.. _AUR: https://wiki.archlinux.org/index.php/AUR
.. _AUR Helper: https://wiki.archlinux.org/index.php/AUR_Helpers
.. _qtile: https://aur.archlinux.org/packages/qtile/
.. _qtile-python3-git: https://aur.archlinux.org/packages/qtile-python3-git/
