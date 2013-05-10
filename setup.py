#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

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

setup(
    name="qtile",
    version="0.6",
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
    url="http://qtile.org",
    license="MIT",
    include_package_data=True,
    packages=find_packages(),
    scripts=[
        "bin/qsh",
        "bin/qtile",
        "bin/qtile-session"
    ],
)
