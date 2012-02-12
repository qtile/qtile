Installing on Arch Linux
==================

Contents

- `Dependecies <http://localhost:8000/html/manual/install/arch.html#dependencies>`_
- `Installation <http://localhost:8000/html/manual/install/arch.html#installation>`_

Dependencies
++++++++++++
You can download the dependencies from the AUR_.

- qtile-git_
- cairo-xcb_
- pycairo-xcb-git_
- xpyb-git_

Other dependencies may include:

- pygtk  (`32-Bit <http://www.archlinux.org/packages/extra/i686/pygtk/>`_/ `64-Bit <http://www.archlinux.org/packages/extra/x86_64/pygtk/>`_)  
- python2 (`32-Bit <http://www.archlinux.org/packages/extra/i686/python2/>`_/ `64-Bit <http://www.archlinux.org/packages/extra/x86_64/python2/>`_)  

.. _AUR: http://aur.archlinux.org/
.. _qtile-git: http://aur.archlinux.org/packages.php?ID=20172
.. _cairo-xcb: http://aur.archlinux.org/packages.php?ID=40641
.. _pycairo-xcb-git: http://aur.archlinux.org/packages.php?ID=43939
.. _xpyb-git: http://aur.archlinux.org/packages.php?ID=40922

Installation
++++++++++++

Installation via AUR-helper
---------------------------

The easiest way to install package from AUR is to use one of AUR-helper
from this `list <https://wiki.archlinux.org/index.php/AUR_Helpers>`_

For example, if you use yaourt:

::

   yaourt -S qtile-git


Installation via pacman and AUR
-------------------------------

We'll start with the cairo-xcb package:

Installing cairo-xcb
~~~~~~~~~~~~~~~~~~~~

::

   tar -xvzf cairo-xcb-{vernum}
   cd cairo-xcb-{vernum}
   makepkg -s
   
Once it has finished making install the package with pacman like so:

::

   sudo pacman -U <packagename>

Allow the package to install and we can move onto the next packages.

Installing pycairo
~~~~~~~~~~~~~~~~~~

::

   tar -xvzf pycairo-xcb-git-{vernum}
   cd pycairo-xcb-git-{vernum}
   makepkg -s
   
Once it has finished making install the package with pacman like so:

::

   sudo pacman -U <packagename>

Allow the package to install and we can move onto the next packages.

Installing xpyb-git
~~~~~~~~~~~~~~~~~~~

::

   tar -xvzf xpyb-git-{vernum}
   cd xpyb-git-{vernum}
   makepkg -s
   
Once it has finished making install the package with pacman like so:

::

   sudo pacman -U <packagename>

Allow the package to install and we can move onto installing Qtile proper.

Installing qtile
~~~~~~~~~~~~~~~~

::

   tar -xvzf qtile-git-{vernum}
   cd qtile-git-{vernum}
   makepkg -s
   
Once it has finished making install the package with pacman like so:

::

   sudo pacman -U <packagename>

Qtile should now be installed on your ArchLinux system. Please refer to the 
`configuration`  documentation to see how to configure your installation for 
first use.
