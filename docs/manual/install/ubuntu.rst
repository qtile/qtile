==============================
Installing on Ubuntu or Debian
==============================

Newer versions of Debian-based distros (Debian >= 13, Ubuntu >= 25.04) have
Qtile packages. Exact versions for each distro release can be found either on
packages.debian.org_ or packages.ubuntu.com_

.. _packages.debian.org: https://packages.debian.org/search?keywords=qtile
.. _packages.ubuntu.com: https://packages.ubuntu.com/search?keywords=qtile&searchon=names&section=all


Older Releases
==============

Ubuntu and Debian >=11 comes with the necessary packages for installing Qtile.
Starting from a minimal Debian installation, the following packages are
required:

.. code-block:: bash

   sudo apt install xserver-xorg xinit
   sudo apt install libpangocairo-1.0-0
   sudo apt install uv  # if your distro doesn't have uv, try:
   # curl -LsSf https://astral.sh/uv/install.sh | sh



Either Qtile can then be downloaded from the package index or the Github 
repository can be used, see :ref:`installing-from-source`:

.. code-block:: bash

   uv tool install qtile
