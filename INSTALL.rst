Dependencies
============

Qtile has a set of dependencies that currently need to be installed from fresh
repository checkouts. This will become much simpler once the new features we
depend on make it into distros, but until then, please follow the instructions_
in the Qtile documentation.

.. _instructions: http://qtile.org/doc-current/index.html


Installation
============

  #.  Install the Qtile library and executables::

        python setup.py install

  #.  Create a Qtile configuration directory and create a configuration file.
      It is probably easiest to start with one of the configuration files
      in the ``examples/config`` directory of the Qtile distribution::

        mkdir ~/.config/qtile

        cp examples/config/cortesi-config.py ~/.config/qtile/config.py

  #.  Make Qtile run. On my system, this meant creating an ``.xsession`` file
      containing the following

      .. code-block:: sh

        #!/bin/sh
        exec /usr/bin/qtile

