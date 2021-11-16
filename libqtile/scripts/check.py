# Copyright (c) 2020, Tycho Andersen. All rights reserved.
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

# Set the locale before any widgets or anything are imported, so any widget
# whose defaults depend on a reasonable locale sees something reasonable.
import shutil
import subprocess
import tempfile
from os import environ, path
from pathlib import Path

import typer
from typer import Option

from libqtile import confreader


def type_check_config_vars(tempdir, config_name):
    if shutil.which("stubtest") is None:
        print("stubtest not found, can't type check config file\n"
              "install it and try again")
        return

    # write a .pyi file to tempdir:
    f = open(path.join(tempdir, config_name+".pyi"), "w")
    f.write(confreader.config_pyi_header)
    for name, type_ in confreader.Config.__annotations__.items():
        f.write(name)
        f.write(": ")
        f.write(type_)
        f.write("\n")
    f.close()

    # need to tell python to look in pwd for modules
    newenv = environ.copy()
    newenv["PYTHONPATH"] = newenv.get("PYTHONPATH", "") + ":"

    p = subprocess.Popen(
        ["stubtest", "--concise", config_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tempdir,
        text=True,
        env=newenv,
    )
    stdout, stderr = p.communicate()
    missing_vars = []
    for line in (stdout+stderr).split("\n"):
        # filter out stuff that users didn't specify; they'll be imported from
        # the default config
        if "is not present at runtime" in line:
            missing_vars.append(line.split()[0])

    # write missing vars to a tempfile
    whitelist = open(path.join(tempdir, "stubtest_whitelist"), "w")
    for var in missing_vars:
        whitelist.write(var)
        whitelist.write("\n")
    whitelist.close()

    p = subprocess.Popen([
            "stubtest",
            # ignore variables that the user creates in their config that
            # aren't in our default config list
            "--ignore-missing-stub",
            # use our whitelist to ignore stuff users didn't specify
            "--whitelist", whitelist.name,
            config_name,
        ],
        cwd=tempdir,
        text=True,
        env=newenv,
    )
    p.wait()
    if p.returncode != 0:
        typer.Exit(code=1)


def type_check_config_args(config_file):
    if shutil.which("mypy") is None:
        print("mypy not found, can't type check config file"
              "install it and try again")
        return
    try:
        # we want to use Literal, which is in 3.8. If people have a mypy that
        # is too old, they can upgrade; this is an optional check anyways.
        subprocess.check_call(["mypy", "--python-version=3.8", config_file])
        print("config file type checking succeeded")
    except subprocess.CalledProcessError as e:
        print("config file type checking failed: {}".format(e))
        typer.Exit(code=1)


def check(
    configfile: Path = Option(
        confreader.path, "-c", "--config", help="Use the specified configuration file."
    ),
):
    """
    Check a configuration file for errors.
    """
    print("Checking Qtile config file:", configfile)

    # need to do all the checking in a tempdir because we need to write stuff
    # for stubtest
    with tempfile.TemporaryDirectory() as tempdir:
        shutil.copytree(configfile.parent, tempdir, dirs_exist_ok=True)
        tmp_path = path.join(tempdir, configfile.name)

        # are the top level config variables the right type?
        type_check_config_vars(tempdir, configfile.stem)

        # are arguments passed to qtile APIs correct?
        type_check_config_args(tmp_path)

    # can we load the config?
    config = confreader.Config(configfile)
    config.load()
    config.validate()
    print("Config file can be loaded by Qtile.")
