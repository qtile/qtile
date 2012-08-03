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

    curl "http://keyserver.ubuntu.com:11371/pks/lookup?op=get&search=0x8516D5EEF453E809" > tyco.key
    sudo apt-key add tyco.key

and finally install with:

.. code-block:: bash

    sudo aptitude update
    sudo aptitude install qtile

To get up and running copy the default config file.

.. code-block:: bash

    mkdir -p ~/.config/qtile
    cp /usr/lib/pymodules/python2.7/libqtile/resources/default-config.py ~/.config/qtile/config.py
