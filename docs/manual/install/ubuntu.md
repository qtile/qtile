==============================
Installing on Ubuntu or Debian 11 (bullseye) or greater
==============================

Ubuntu and Debian >=11 comes with the necessary packages for installing Qtile.
Starting from a minimal Debian installation, the following packages are
required:

.. code-block:: bash

   sudo apt install xserver-xorg xinit
   sudo apt install libpangocairo-1.0-0
   sudo apt install python3-pip python3-xcffib python3-cairocffi


Either Qtile can then be downloaded from the package index or the Github 
repository can be used, see :ref:`installing-from-source`:

.. code-block:: bash

   pip install qtile
