==============================
Installing on Debian or Ubuntu
==============================

Note: As of Ubuntu 20.04 (Focal Fossa), the package has been outdated
and removed from the Ubuntu's official package list.
Users are advised to follow the instructions of :ref:`installing-from-source`.

On other recent Ubuntu (17.04 or greater) and Debian unstable versions,
there are Qtile packages available via:

.. code-block:: bash

    sudo apt-get install qtile

On older versions of Ubuntu (15.10 to 16.10) and Debian 9, the
dependencies are available via:

.. code-block:: bash

    sudo apt-get install python3-xcffib python3-cairocffi


Debian 11 (bullseye)
--------------------

Debian 11 comes with the necessary packages for installing Qtile. Starting 
from a minimal Debian installation, the following packages are required:

.. code-block:: bash

   sudo apt install xserver-xorg xinit
   sudo apt install libpangocairo-1.0-0
   sudo apt install python3-pip python3-xcffib python3-cairocffi


Either Qtile can then be downloaded from the package index or the Github 
repository can be used, see :ref:`installing-from-source`:

.. code-block:: bash

   pip install qtile
