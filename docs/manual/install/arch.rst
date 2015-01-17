========================
Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as:

- `qtile-git`_ development branch of qtile.
- `qtile-python3-git`_ development branch of qtile for python3.
- `qtile`_ stable branch(release) of qtile.

Using an AUR Helper
===================

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use `yaourt`_:

.. code-block:: bash

    # for release
    yaourt -S qtile
    # or for develop
    yaourt -S qtile-git
    # or for develop python3
    yaourt -S qtile-python3-git

Using pacman
============

You can choose python3 or python2

.. code-block:: bash

    # for python3
    sudo pacman -S python pango
    # or for python2
    sudo pacman -S python2 pango

Also you need these packages from AUR:

**For python3:**

- `qtile-python3-git`_
- `python-xcffib`_
- `python-cairocffi`_

**For python2:**

- `qtile-git`_
- `python2-xcffib`_
- `python2-cairocffi`_
- `trollius`_

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
.. _qtile-git: https://aur.archlinux.org/packages/qtile-git/
.. _qtile-python3-git: https://aur.archlinux.org/packages/qtile-python3-git/
.. _python-xcffib: https://aur.archlinux.org/packages/python-xcffib/
.. _python2-xcffib: https://aur.archlinux.org/packages/python2-xcffib/
.. _python-cairocffi: https://aur.archlinux.org/packages/python-cairocffi/
.. _python2-cairocffi: https://aur.archlinux.org/packages/python2-cairocffi/
.. _trollius: https://aur.archlinux.org/packages/python2-trollius/
