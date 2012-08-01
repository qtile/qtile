Installing on Debian
====================

Packages are available from Tycho's Ubuntu PPA repository. 
These are known to work with Debian Wheezy without any observed side effects.

Tych0's ppa is at https://launchpad.net/~tycho-s/+archive/ppa

create file /etc/apt/sources.d/tycho.list with the following:

.. code-block:: bash

    deb http://ppa.launchpad.net/tycho-s/ppa/ubuntu precise main
    deb-src http://ppa.launchpad.net/tycho-s/ppa/ubuntu precise main

Then to install tycho's key from the ppa above:

.. code-block:: bash

    curl "http://keyserver.ubuntu.com:11371/pks/lookup?op=get&search=0x8516D5EEF453E809" | sudo apt-key add

and finally install with:

.. code-block:: bash

    sudo aptitude update install qtile
