========================
Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as:

======================= =======================
Package Name            Description
======================= =======================
`qtile`_                stable branch (release)
`qtile-python3-git`_    development branch
======================= =======================

Using an AUR Helper
===================

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use `yaourt`_:

.. code-block:: bash

    yaourt -S <package-name>

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

Please see the ArchWiki for more information on `installing packages from the AUR`_.

.. _AUR: https://wiki.archlinux.org/index.php/AUR
.. _AUR Helper: https://wiki.archlinux.org/index.php/AUR_Helpers
.. _installing packages from the AUR: https://wiki.archlinux.org/index.php/Arch_User_Repository#Installing_packages
.. _qtile: https://aur.archlinux.org/packages/qtile/
.. _qtile-python3-git: https://aur.archlinux.org/packages/qtile-python3-git/
.. _yaourt: https://archlinux.fr/yaourt-en
