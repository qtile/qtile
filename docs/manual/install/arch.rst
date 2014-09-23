Installing on Arch Linux
========================

Qtile is available on the `AUR`_ as:

- `qtile-git`_ development branch of qtile.
- `qtile-python3-git`_ development branch of qtile for python3.
- `qtile`_ stable branch(release) of qtile.

Using an AUR Helper
-------------------

The preferred way to install Qtile is with an `AUR helper`_. For example,
if you use `yaourt`_:

.. code-block:: bash

    # for release
    yaourt -S qtile
    # or for develop
    yaourt -S qtile-git
    # or for develop python3
    yaourt -S qtile-python3-git

Using pacman for develop
------------------------

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
- `python-cairocffi-xcffib-git`_

**For python2:**

- `qtile-git`_
- `python2-xcffib`_
- `python2-cairocffi-xcffib-git`_
- `trollius`_

Using pacman for release
------------------------

**Packages in Core:**

You need pygtk, python2 and cairo

.. code-block:: bash

    sudo pacman -S pygtk cairo

**Packages in the AUR:**

You need:

- `pycairo-xcb-git`_
- `xorg-xpyb-git`_
- `qtile`_

Installing AUR packages without helper
--------------------------------------

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
.. _pycairo-xcb-git: http://aur.archlinux.org/packages.php?ID=43939
.. _xorg-xpyb-git: http://aur.archlinux.org/packages.php?ID=57865
.. _python-xcffib: https://aur.archlinux.org/packages/python-xcffib/
.. _python2-xcffib: https://aur.archlinux.org/packages/python2-xcffib/
.. _python-cairocffi-xcffib-git: https://aur.archlinux.org/packages/python-cairocffi-xcffib-git/
.. _python2-cairocffi-xcffib-git: https://aur.archlinux.org/packages/python2-cairocffi-xcffib-git/
.. _trollius: https://aur.archlinux.org/packages/python2-trollius/
