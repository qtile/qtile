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

import shutil
import subprocess
import sys
import tempfile
from os import environ, getenv, path

from libqtile import confreader


def type_check_config_vars(tempdir: str, config_name: str) -> bool:
    # write a .pyi file to tempdir:
    f = open(path.join(tempdir, config_name + ".pyi"), "w")
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
    for line in (stdout + stderr).split("\n"):
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

    p = subprocess.Popen(
        [
            "stubtest",
            # ignore variables that the user creates in their config that
            # aren't in our default config list
            "--ignore-missing-stub",
            # use our whitelist to ignore stuff users didn't specify
            "--whitelist",
            whitelist.name,
            config_name,
        ],
        cwd=tempdir,
        text=True,
        env=newenv,
    )
    p.wait()
    return p.returncode == 0


def type_check_config_args(config_file: str) -> bool:
    try:
        subprocess.check_call(["mypy", "--ignore-missing-imports", config_file])
        print("Config file type checking succeeded!")
    except subprocess.CalledProcessError as e:
        print("Config file type checking failed:", e)
        return False
    return True


def _has_deps() -> bool:
    ok = True

    for dep in ["mypy", "stubtest"]:
        if shutil.which(dep) is None:
            print(f"{dep} was not found in PATH. Please install it, add to PATH and try again.")
            ok = False

    return ok


def check_config(args) -> bool:
    if not _has_deps():
        return False

    failed = False
    print("Checking Qtile config at:", args.configfile)

    # need to do all the checking in a tempdir because we need to write stuff
    # for stubtest
    with tempfile.TemporaryDirectory() as tempdir:
        shutil.copytree(path.dirname(args.configfile), tempdir, dirs_exist_ok=True)
        tmp_path = path.join(tempdir, path.basename(args.configfile))

        # are the top level config variables the right type?
        module_name = path.splitext(path.basename(args.configfile))[0]
        if not type_check_config_vars(tempdir, module_name):
            failed = True

        # are arguments passed to qtile APIs correct?
        if not type_check_config_args(tmp_path):
            failed = True

    # can we load the config?
    config = confreader.Config(args.configfile)
    try:
        config.validate()
        print("\nYour config can be loaded by Qtile.")
    except confreader.ConfigError as e:
        print(e)
        print("\nYour config cannot be loaded by Qtile.")

    return failed


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "check", parents=parents, help="Check a configuration file for errors."
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=path.expanduser(
            path.join(getenv("XDG_CONFIG_HOME", "~/.config"), "qtile", "config.py")
        ),
        dest="configfile",
        help="Use the specified configuration file.",
    )
    parser.set_defaults(func=check_config)
