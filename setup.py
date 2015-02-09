# Copyright (c) 2008 Aldo Cortesi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 dmpayton
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Pedro Algarvio
# Copyright (c) 2014-2015 Tycho Andersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#!/usr/bin/env python

# Import python libs
import sys
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

dependencies = ['cairocffi>=0.6', 'cffi>=0.8.2', 'six>=1.4.1', 'xcffib>=0.1.11']

if sys.version_info >= (3, 4):
    pass
elif sys.version_info >= (3, 3):
    dependencies.append('asyncio')
elif sys.version_info <= (2, 6) or \
        (sys.version_info >= (3, 0) and sys.version_info <= (3, 1)):
    dependencies.append('importlib')
else:
    dependencies.append('trollius')

setup(
    name="qtile",
    version="0.9.0",
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
    data_files=[
        ('share/man/man1', ['resources/qtile.1',
                            'resources/qsh.1'])],
)
