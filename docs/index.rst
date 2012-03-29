.. Qtile documentation master file, created by
   sphinx-quickstart on Sat Dec  3 13:11:54 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================================
Welcome to Qtile's documentation!
=================================

Qtile is a full-featured, hackable tiling window manager written in Python.

Contents:

..  toctree::
    :maxdepth: 2

    development


Features
========

* Simple, small and extensible. It's easy to write your own layouts,
  widgets and built-in commands.
* Configured entirely in Python. 
* Command-line shell that allows all aspects of Qtile to be manipulated and
  inspected.
* Complete remote scriptability - write scripts to set up workspaces,
  manipulate windows, update status bar widgets and more.
* Qtile's scriptability has made thorough unit testing possible,
  making it one of the best-tested window managers around.


Dependencies
============

Qtile relies on some cutting-edge features in PyCairo, XCB, and xpyb. Until the
latest versions of these projects make it into distros, it's best to use recent
checkouts from their repositories. Here's a brief step-by-step guide:


libxcb
------

::

  git clone git://anongit.freedesktop.org/git/xcb/libxcb
  cd libxcb
  ./autogen.sh
  make
  sudo make install


xpyb-ng
-------

::

  git clone https://github.com/dequis/xpyb-ng.git
  python setup.py install


cairo
-----

The latest cairo release works, but recompiling with xcb support is needed.

::

  wget http://cairographics.org/releases/cairo-1.10.0.tar.gz
  tar xvzf cairo-1.10.0.tar.gz
  cd cairo-1.10.0
  ./autogen.sh --enable-xcb
  make
  sudo make install


py2cairo
--------

::

  git clone git://git.cairographics.org/git/py2cairo
  cd py2cairo
  ./autogen.sh --enable-xcb

Check the configure output to make sure that XPYB is correctly detected.

::

  make
  sudo make install


PyGTK
-----

We also require a reasonably recent version of the Python GTK bindings, in
particular, the ``pango`` module. You should just be able to install this using
your chosen distribution's package manager.



If you plan to run the test suite, you will also need nose_, and the
`Python X Library`_.

..  _nose: http://readthedocs.org/docs/nose/en/latest/
..  _Python X Library: http://python-xlib.sourceforge.net/



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

