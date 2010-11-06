from distutils.core import setup

long_description = """
A pure-Python tiling window manager.

Features
========

    * Simple, small and extensible. It's easy to write your own layouts,
      widgets and commands.
    * Configured in Python.
    * Command shell that allows all aspects of Qtile to be managed and inspected.
    * Complete remote scriptability - write scripts to set up workspaces,
      manipulate windows, update status bar widgets and more. 
    * Qtile's remote scriptability makes it one of the most thoroughly
      unit-tested window mangers around.

Qtile depends on the Python X Library (http://python-xlib.sourceforge.net/).
"""

"""
    The content below is included from the distextend project.

    The code is in the public domain, and may be used for any purpose
    whatsoever.
"""
import fnmatch, os.path

def _fnmatch(name, patternList):
    for i in patternList:
        if fnmatch.fnmatch(name, i):
            return True
    return False


def _splitAll(path):
    parts = []
    h = path
    while 1:
        if not h:
            break
        h, t = os.path.split(h)
        parts.append(t)
    parts.reverse()
    return parts


def findPackages(path, dataExclude=[]):
    """
        Recursively find all packages and data directories rooted at path. Note
        that only data _directories_ and their contents are returned -
        non-Python files at module scope are not, and should be manually
        included.
        
        dataExclude is a list of fnmatch-compatible expressions for files and
        directories that should not be included in pakcage_data.

        Returns a (packages, package_data) tuple, ready to be passed to the
        corresponding distutils.core.setup arguments.
    """
    packages = []
    datadirs = []
    for root, dirs, files in os.walk(path, topdown=True):
        if "__init__.py" in files:
            p = _splitAll(root)
            packages.append(".".join(p))
        else:
            dirs[:] = []
            if packages:
                datadirs.append(root)

    package_data = {}
    for i in datadirs:
        if not _fnmatch(i, dataExclude):
            parts = _splitAll(i)
            module = ".".join(parts[:-1])
            acc = package_data.get(module, [])
            for root, dirs, files in os.walk(i, topdown=True):
                sub = os.path.join(*_splitAll(root)[1:])
                if not _fnmatch(sub, dataExclude):
                    for fname in files:
                        path = os.path.join(sub, fname)
                        if not _fnmatch(path, dataExclude):
                            acc.append(path)
                else:
                    dirs[:] = []
            package_data[module] = acc
    return packages, package_data

packages, package_data = findPackages("libqtile")


setup(
        name = "qtile",
        version = "0.4",
        description="A pure-Python tiling window manager.",
        author="Aldo Cortesi",
        author_email="aldo@nullcube.com",
        license="MIT",
        url="http://www.qtile.org",
        packages = packages,
        package_data = package_data,
        scripts = ["qtile", "qsh"],
        classifiers = [
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: MIT License",
            "Development Status :: 3 - Alpha",
            "Programming Language :: Python",
            "Operating System :: Unix",
            "Topic :: Desktop Environment :: Window Managers",
        ]
)
