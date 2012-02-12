Installing on Arch Linux
==================

Contents

- `Dependecies <http://localhost:8000/html/manual/install/arch.html#dependencies>`_
- `Installation <http://localhost:8000/html/manual/install/arch.html#installation>`_

Dependencies
++++++++++++
In order to install Qtile we need to download several packages from the AUR_.

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

We'll start with the cairo-xcb package:

.. code-block:: bash

   tar -xvzf cairo-xcb-{vernum}
   cd cairo-xcb-{vernum}
   makepkg -s
   
Once it has finished making the package

.. code-block:: bash

   sudo pacman -U <packagename>

Allow the package to install and we can move onto the next packages.





