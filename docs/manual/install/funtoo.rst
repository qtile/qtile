Installing on Funtoo
====================

Portage
-------

The ebuild in portage is broken for now, as of missing xpyb support for pycairo, but will be fixed in some future releases.

Manual (Github)
---------------

This section is taken from the documents from Qtile. [#]_.

Dependencies
~~~~~~~~~~~~

USE flags and keyword changes may have to be made for the packages taken from portage.

libxcb
~~~~~~

libxcb can be emerged from portage.

.. code-block:: bash

    # emerge -avt libxcb


xpyb
~~~~

xpyb can be emerged from portage. Make sure that you are emerging xpyb-1.3.1 or above.

.. code-block:: bash

    # emerge -avt xpyb


cairo
~~~~~

cairo can be emerged from portage. Make sure you have your USE flags set to:

.. code-block:: bash

   X glib opengl svg xcb

and then emerge cairo:

.. code-block:: bash

    # emerge -avt cairo

pygtk
~~~~~

pygtk can be merged from portage.

.. code-block:: bash

    # emerge pygtk


py2cairo
~~~~~~~~

Needs to be build manually cause of reason above.

.. code-block:: bash

    # git clone git://git.cairographics.org/git/py2cairo
    # cd py2cairo
    # ./configure --prefix=/path/to/virtualenv
    # make
    # sudo make install

As an alternative to virtualenv, you can

.. code-block:: bash

    ./configure --prefix=/usr

But the virtualenv is the recommended option in installation if you are an advanced user with python, else use the systemwide alternative.

qtile
~~~~~

.. code-block:: bash

    # git clone git://github.com/qtile/qtile
    # cd qtile
    # sudo python setup.py install --record files_uninstall.txt

Setup
-----

**Copy** either a config from the examples directory in the cloned qtile **(including a default config)**, a config you have found elsewhere, or create your own config.

.. code-block:: bash

    # install -d ~/.config/qtile
    # cp /path/to/cloned-qtile/examples/config/cortesi-config.py ~/.config/qtile/config.py
    # cp /path/to/cloned-qtile/examples/config/dgroups.py ~/.config/qtile/config.py
    # cp /path/to/cloned-qtile/examples/config/roger-config.py ~/.config/qtile/config.py
    # cp /path/to/cloned-qtile/examples/config/tailhook-config.py ~/.config/qtile/config.py

Another config is `config.py <https://github.com/akiress/dotfiles/blob/master/qtile/config.py>`_, this is based on `dmpayton's config.py <https://github.com/dmpayton/dotfiles/blob/master/qtile/config.py>`_.

Testing Qtile Installation
--------------------------

If you have a running DE/WM already you can test your qtile config with the following steps:

Examples:

.. code-block:: bash

    # Xephyr :1 -screen 800x600 -a -v -noreset
    # Display=:1
    # /path/to/qtile/qtile

or using the build in code: [#]_

.. code-block:: bash

    # echo "exec qtile" > .start_qtile ; xinit .start_qtile -- :1

For further information, see the Documentation section.

dmenu
-----

Qtile uses dmenu as the application launcher

.. code-block:: bash
    # emerge dmenu

xinitrc
-------

An example of preparing Qtile to start with the startup-session script for autostarting apps in the ~/.xinitrc:

.. code-block:: bash

    #!/bin/zsh
    xrdb -merge ~/.Xresources
    xcompmgr &
    if [[ $1 == "i3" ]]; then
        exec ck-launch-session dbus-launch --sh-syntax --exit-with-session i3 -V -d all > ~/.i3/i3log-$(date +'%F-%k-%M-%S') 2>&1
    elif [[ $1 == "razor" ]]; then
        exec ck-launch-session dbus-launch startrazor
    elif [[ $1 == "awesome" ]]; then
        exec ck-launch-session dbus-launch awesome
    elif [[ $1 == "qtile" ]]; then
        exec ck-launch-session dbus-launch ~/.qtile-session
    else
        echo "Choose a window manager"
    fi

and the connected ~/.qtile-session

.. code-block:: bash

    conky -c ~/.conky/conkyrc_grey &
    sh ~/.fehbg &
    dropbox &

X and RandR
-----------

**NOTE: RandR and Xinerama do not play together. Use one or the other.**
I use an AMD HD 6870 with 3 monitors (2 DVI and 1 with an AMD validated Mini DisplayPort™ to DVI dongle).

Install xrandr:

.. code-block:: bash

    # emerge x11-apps/xrandr

and if you want a GUI with xrandr:

.. code-block:: bash

    # emerge x11-misc/arandr

If you do not have X configured yet, follow the link on the `Gentoo Wiki <http://en.gentoo-wiki.com/wiki/X.Org>`_.

My xorg.conf.d folder for example: `30-screen.conf <https://github.com/akiress/dotfiles/blob/master/etc/X11/xorg.conf.d/30-screen.conf>`_.

Since the names of the monitors are already known in xrandr, I just use those names in my 30-screen.conf configuration. It doesn't matter what you use in your X configuration however.

Once you have X configured however you like, start qtile with either:

.. code-block:: bash

    # startx

or, in a case similar to mine,

.. code-block:: bash

    # xinit qtile

Starting with CDM
-----------------

Another good tool for starting qtile is **CDM** (short for Console Display Manager). To make it work, just merge cdm

.. code-block:: bash

    # emerge -avt cdm

and add it to autostart with

.. code-block:: bash

    # cp /usr/share/cdm/zzz-cdm-profile.sh /etc/profile.d/zzz-cdm-profile.sh

Now add to /etc/X11/cdm/cdmrc the following lines:

.. code-block:: bash

    binlist=(
        "/usr/bin/xinit ${HOME}/.start_qtile --:0"
        "/bin/bash --login"
        "/bin/zsh"
    )
    namelist=(qtile "Console bash" "Console zsh")
    flaglist=(C C C)
    consolekit=no

and check that ${HOME}/.start_qtile contains just the following

.. code-block:: bash

    exec qtile

.. [#] `Installation on Gentoo <http://docs.qtile.org/en/latest/manual/install/gentoo.html>`_
.. [#] `https://groups.google.com/group/qtile-dev/browse_thread/thread/26191253a8190568_qtile-dev_Google_Group <https://groups.google.com/group/qtile-dev/browse_thread/thread/26191253a8190568_qtile-dev_Google_Group>`_
