========================
Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as:

- `qtile`_ stable branch(release) of qtile.
- `qtile-python3-git`_ development branch of qtile.

Using an AUR Helper
===================

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use `yaourt`_:

.. code-block:: bash

    # for release
    yaourt -S qtile
    # or for develop
    yaourt -S qtile-python3-git

Using pacman
============

.. code-block:: bash

    sudo pacman -S python pango python-cairocffi python-xcffib

Also you need one qtile package from the AUR:

- `qtile-python3-git`_ 
- `qtile`_ 


Installing AUR packages without helper
======================================

To install these packages, download the .tar.gz's from the AUR and run the
following commands for each:

.. code-block:: bash

    tar -xvzf <packagename>-<vernum>.tar.gz
    cd <packagename>-<vernum>
    makepkg -s
    sudo pacman -U <packagename>

Please see the Arch Wiki for more information on installing packages from
the AUR:

http://wiki.archlinux.org/index.php/AUR#Installing_packages

.. _AUR: https://wiki.archlinux.org/index.php/AUR
.. _AUR Helper: http://wiki.archlinux.org/index.php/AUR_Helpers
.. _yaourt: http://wiki.archlinux.org/index.php/Yaourt
.. _qtile: https://aur.archlinux.org/packages/qtile/
.. _qtile-python3-git: https://aur.archlinux.org/packages/qtile-python3-git/
