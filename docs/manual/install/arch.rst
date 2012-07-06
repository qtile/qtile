Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as `qtile-git`_.

Using an AUR Helper
-------------------

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use `yaourt`_:

.. code-block:: bash

    yaourt -S qtile-git

Using pacman
------------

**Packages in Core:**

- pygtk (`32-Bit <http://www.archlinux.org/packages/extra/i686/pygtk/>`_ / `64-Bit <http://www.archlinux.org/packages/extra/x86_64/pygtk/>`_)
- python2 (`32-Bit <http://www.archlinux.org/packages/extra/i686/python2/>`_ / `64-Bit <http://www.archlinux.org/packages/extra/x86_64/python2/>`_)
- cairo (`32-Bit <http://www.archlinux.org/packages/extra/i686/cairo/>`_ / `64-Bit <http://www.archlinux.org/packages/extra/x86_64/cairo/>`_)

If you don't have these already, they can be installed with:

.. code-block:: bash

    sudo pacman -S pygtk python2 cairo

**Packages in the AUR:**

- `pycairo-xcb-git`_
- `xorg-xpyb-git`_
- `qtile-git`_

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
.. _qtile-git: http://aur.archlinux.org/packages.php?ID=20172
.. _pycairo-xcb-git: http://aur.archlinux.org/packages.php?ID=43939
.. _xorg-xpyb-git: http://aur.archlinux.org/packages.php?ID=57865
