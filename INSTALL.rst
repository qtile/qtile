Dependencies
============

Qtile has a set of dependencies that currently need to be installed from fresh
repository checkouts. This will become much simpler once the new features we
depend on make it into distros, but until then, please follow the instructions_
in the Qtile documentation.

.. _instructions: http://docs.qtile.org/en/latest/manual/install/index.html


Installation
============

#.  Install the Qtile library and executables::

      python setup.py install

#.  Create a Qtile configuration directory and create a configuration file.
    It is probably easiest to start with one of the configuration files
    in the ``qtile-examples`` repository::

      mkdir ~/.config/qtile
      git clone https://github.com/qtile/qtile-examples.git
      cp qtile-examples/config/config.py ~/.config/qtile/config.py

#.  Make Qtile run as your window manager. If you are using a login manager,
    you can just do::

      sudo cp resources/qtile.desktop /usr/share/xsessions

    and select 'Qtile' as your session type. More information on starting qtile
    is available in the documentation_.

.. _documentation: http://qtile.readthedocs.org/en/latest/manual/config/starting.html

