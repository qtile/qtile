#!/usr/bin/env python

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

if '_cffi_backend' in sys.builtin_module_names:
    import _cffi_backend
    requires_cffi = "cffi==" + _cffi_backend.__version__
else:
    requires_cffi = "cffi>=1.1.0"

# PyPy < 2.6 compatibility
if requires_cffi.startswith("cffi==0."):
    cffi_args = dict(
        zip_safe=False
    )
else:
    cffi_args = dict(cffi_modules=[
        'libqtile/ffi_build.py:pango_ffi',
        'libqtile/ffi_build.py:xcursors_ffi'
    ])

dependencies = ['xcffib>=0.3.2', 'cairocffi>=0.7[xcb]', 'six>=1.4.1', requires_cffi]

if sys.version_info >= (3, 4):
    pass
elif sys.version_info >= (3, 3):
    dependencies.append('asyncio')
else:
    dependencies.append('trollius')

if (3, 0) <= sys.version_info <= (3, 1):
    dependencies.append('importlib')

setup(
    name="qtile",
    version="0.9.1",
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
    **cffi_args
)
