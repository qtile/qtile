#!/usr/bin/env python

# Import python libs
try:
    from setuptools import setup
except ImportError:
    # Let's not fail if setuptools is not available
    from distutils.core import setup

long_description = """
A pure-Python tiling window manager.

Features
========

    * Simple, small and extensible. It's easy to write your own layouts,
      widgets and commands.
    * Configured in Python.
    * Command shell that allows all aspects of
      Qtile to be managed and inspected.
    * Complete remote scriptability - write scripts to set up workspaces,
      manipulate windows, update status bar widgets and more.
    * Qtile's remote scriptability makes it one of the most thoroughly
      unit-tested window mangers around.
"""

import libqtile.pangocffi

dependencies = ['six', 'cffi>=0.8.2']

setup(
    name="qtile",
    version="0.7.0",
    description="A pure-Python tiling window manager.",
    long_description=long_description,
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Operating System :: Unix",
        "Topic :: Desktop Environment :: Window Managers",
    ],
    keywords="qtile tiling window manager",
    author="Aldo Cortesi",
    author_email="aldo@nullcube.com",
    maintainer="Tycho Andersen",
    maintainer_email="tycho@tycho.ws",
    url="http://qtile.org",
    license="MIT",
    install_requires=dependencies,
    setup_requires=dependencies,
    packages=['libqtile',
              'libqtile.layout',
              'libqtile.widget',
              'libqtile.resources'
    ],
    package_data={'libqtile.resources': ['battery-icons/*.png']},
    scripts=[
        "bin/qsh",
        "bin/qtile",
        "bin/qtile-run",
        "bin/qtile-session"
    ],
)
