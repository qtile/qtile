# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import importlib
import io
import logging
import os
import pickle
import sys
import traceback
import warnings
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from libqtile import hook, utils, window
from libqtile.backend.x11 import xcbq
from libqtile.backend.x11.xcore import XCore
from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import QtileCommandInterface
from libqtile.command_object import (
    CommandError,
    CommandException,
    CommandObject,
)
from libqtile.config import Match, Rule
from libqtile.confreader import Config, ConfigError
from libqtile.log_utils import logger
from libqtile.state import QtileState
from libqtile.utils import get_cache_dir

if TYPE_CHECKING:
    from libqtile.core.manager import Qtile


def validate_config(file_path):
    """
    Validate a configuration file.

    This function reloads and imports the given configuration file.
    It re-raises a ConfigError with a detailed message for any caught exception.
    """
    output = [
        "The configuration file '",
        file_path,
        "' generated the following error:\n\n",
    ]

    # Get the module name from the file path
    name = os.path.splitext(os.path.basename(file_path))[0]

    try:
        # Mandatory: we must reload the module (the config file was modified)
        importlib.reload(sys.modules[name])
    except KeyError:
        # The module name didn't match the file path basename. Abort.
        return

    try:
        Config.from_file(XCore(), file_path)

    except ConfigError as error:
        output.append(str(error))
        raise ConfigError("".join(output))

    except Exception as error:
        # Handle SyntaxError and the likes
        output.append("{}: {}".format(sys.exc_info()[0].__name__, str(error)))
        raise ConfigError("".join(output))


def send_notification(title, message, timeout=10000):
    """Send a notification."""
    import gi

    gi.require_version("Notify", "0.7")
    from gi.repository import Notify

    Notify.init("Qtile")
    notifier = Notify.Notification.new(title, message)
    notifier.set_timeout(timeout)
    notifier.show()


def _import_module(module_name, dir_path):
    import imp

    fp = None
    try:
        fp, pathname, description = imp.find_module(module_name, [dir_path])
        module = imp.load_module(module_name, fp, pathname, description)
    finally:
        if fp:
            fp.close()
    return module


class CommandRoot(CommandObject):
    """This object is the `root` of the command graph"""

    def __init__(self, qtile: "Qtile") -> None:
        self._qtile = qtile

    def _items(self, name) -> Tuple[bool, List[Union[str, int]]]:
        if name == "group":
            return True, list(self._qtile.groups_map.keys())
        elif name == "layout":
            return True, list(range(len(self._qtile.current_group.layouts)))
        elif name == "widget":
            return False, list(self._qtile.widgets_map.keys())
        elif name == "bar":
            return False, [x.position for x in self._qtile.current_screen.gaps]
        elif name == "window":
            return True, self._qtile.list_wids()
        elif name == "screen":
            return True, list(range(len(self._qtile.screens)))

        raise ValueError("Invalid name: {name}".format(name=name))

    def _select(self, name: str, sel: Optional[Union[str, int]]) -> CommandObject:
        if name == "group":
            if sel is None:
                return self._qtile.current_group
            else:
                return self._qtile.groups_map.get(sel)
        elif name == "layout":
            if sel is None:
                return self._qtile.current_group.layout
            else:
                return utils.lget(self._qtile.current_group.layouts, sel)
        elif name == "widget":
            return self._qtile.widgets_map.get(sel)
        elif name == "bar":
            assert sel is not None and not isinstance(sel, int)
            return getattr(self._qtile.current_screen, sel)
        elif name == "window":
            if sel is None:
                return self._qtile.current_window
            else:
                return self._qtile.client_from_wid(sel)
        elif name == "screen":
            if sel is None:
                return self._qtile.current_screen
            else:
                return utils.lget(self._qtile.screens, sel)

        raise ValueError("Invalid name: {name}".format(name=name))

    def cmd_focus_by_click(self, e) -> None:
        """Bring a window to the front

        Parameters
        ==========
        e : xcb event
            Click event used to determine window to focus
        """
        self._qtile.focus_by_click(e)

    def cmd_debug(self) -> None:
        """Set log level to DEBUG"""
        logger.setLevel(logging.DEBUG)
        logger.debug("Switching to DEBUG threshold")

    def cmd_info(self) -> None:
        """Set log level to INFO"""
        logger.setLevel(logging.INFO)
        logger.info("Switching to INFO threshold")

    def cmd_warning(self) -> None:
        """Set log level to WARNING"""
        logger.setLevel(logging.WARNING)
        logger.warning("Switching to WARNING threshold")

    def cmd_error(self) -> None:
        """Set log level to ERROR"""
        logger.setLevel(logging.ERROR)
        logger.error("Switching to ERROR threshold")

    def cmd_critical(self) -> None:
        """Set log level to CRITICAL"""
        logger.setLevel(logging.CRITICAL)
        logger.critical("Switching to CRITICAL threshold")

    def cmd_loglevel(self) -> int:
        return logger.level

    def cmd_loglevelname(self) -> None:
        return logging.getLevelName(logger.level)

    def cmd_pause(self) -> None:
        """Drops into pdb"""
        import pdb

        pdb.set_trace()

    def cmd_groups(self):
        """Return a dictionary containing information for all groups

        Examples
        ========

            groups()
        """
        return {i.name: i.info() for i in self._qtile.groups}

    def cmd_get_info(self):
        """Prints info for all groups"""
        warnings.warn(
            "The `get_info` command is deprecated, use `groups`", DeprecationWarning
        )
        return self._qtile.cmd_groups()

    def cmd_display_kb(self, *args):
        """Display table of key bindings"""

        class FormatTable:
            def __init__(self):
                self.max_col_size = []
                self.rows = []

            def add(self, row):
                n = len(row) - len(self.max_col_size)
                if n > 0:
                    self.max_col_size += [0] * n
                for i, f in enumerate(row):
                    if len(f) > self.max_col_size[i]:
                        self.max_col_size[i] = len(f)
                self.rows.append(row)

            def getformat(self):
                format_string = " ".join(
                    "%-{0:d}s".format(max_col_size + 2)
                    for max_col_size in self.max_col_size
                )
                return format_string + "\n", len(self.max_col_size)

            def expandlist(self, list, n):
                if not list:
                    return ["-" * max_col_size for max_col_size in self.max_col_size]
                n -= len(list)
                if n > 0:
                    list += [""] * n
                return list

            def __str__(self):
                fmt, n = self.getformat()
                return "".join(
                    fmt % tuple(self.expandlist(row, n)) for row in self.rows
                )

        result = FormatTable()
        result.add(["KeySym", "Mod", "Command", "Desc"])
        result.add([])
        rows = []
        for (ks, kmm), k in self._qtile.keys_map.items():
            if not k.commands:
                continue
            name = ", ".join(xcbq.rkeysyms.get(ks, ("<unknown>",)))
            modifiers = ", ".join(xcbq.translate_modifiers(kmm))
            allargs = ", ".join(
                [repr(value) for value in k.commands[0].args]
                + [
                    "%s = %s" % (keyword, repr(value))
                    for keyword, value in k.commands[0].kwargs.items()
                ]
            )
            rows.append(
                (
                    name,
                    str(modifiers),
                    "{0:s}({1:s})".format(k.commands[0].name, allargs),
                    k.desc,
                )
            )
        rows.sort()
        for row in rows:
            result.add(row)
        return str(result)

    def cmd_list_widgets(self) -> List[str]:
        """List of all addressible widget names"""
        return list(self._qtile.widgets_map.keys())

    def cmd_to_layout_index(self, index, group=None) -> None:
        """Switch to the layout with the given index in self.layouts.

        Parameters
        ==========
        index :
            Index of the layout in the list of layouts.
        group :
            Group name. If not specified, the current group is assumed.
        """
        self._qtile.to_layout_index(index, group=group)
        if group:
            group = self._qtile.groups_map.get(group)
        else:
            group = self._qtile.current_group
        group.use_layout(index)

    def cmd_next_layout(self, group=None) -> None:
        """Switch to the next layout.

        Parameters
        ==========
        group :
            Group name. If not specified, the current group is assumed
        """
        if group:
            group = self._qtile.groups_map.get(group)
        else:
            group = self._qtile.current_group
        group.use_next_layout()

    def cmd_prev_layout(self, group: Optional[str] = None) -> None:
        """Switch to the previous layout.

        Parameters
        ==========
        group :
            Group name. If not specified, the current group is assumed
        """
        if group:
            group_ = self._qtile.groups_map.get(group)
        else:
            group_ = self._qtile.current_group
        group_.use_previous_layout()

    def cmd_screens(self) -> List[Dict]:
        """Return a list of dictionaries providing information on all screens"""
        lst = [
            dict(
                index=i.index,
                group=i.group.name if i.group is not None else None,
                x=i.x,
                y=i.y,
                width=i.width,
                height=i.height,
                gaps=dict(
                    top=i.top.geometry() if i.top else None,
                    bottom=i.bottom.geometry() if i.bottom else None,
                    left=i.left.geometry() if i.left else None,
                    right=i.right.geometry() if i.right else None,
                ),
            )
            for i in self._qtile.screens
        ]
        return lst

    def cmd_simulate_keypress(self, modifiers, key) -> None:
        """Simulates a keypress on the focused window.

        Parameters
        ==========
        modifiers :
            A list of modifier specification strings. Modifiers can be one of
            "shift", "lock", "control" and "mod1" - "mod5".
        key :
            Key specification.

        Examples
        ========
            simulate_keypress(["control", "mod2"], "k")
        """
        # FIXME: This needs to be done with sendevent, once we have that fixed.
        try:
            modmasks = xcbq.translate_masks(modifiers)
            keysym = xcbq.keysyms.get(key)
        except xcbq.XCBQError as e:
            raise CommandError(str(e))

        class DummyEv:
            def __init__(self, detail, state):
                self.detail = detail
                self.state = state

        d = DummyEv(self._qtile.conn.first_sym_to_code[keysym], modmasks)
        self._qtile.core.handle_KeyPress(d)

    def cmd_restart(self) -> None:
        """Restart qtile"""
        try:
            validate_config(self._qtile.config.file_path)
        except ConfigError as error:
            logger.error(
                "Preventing restart because of a configuration error: " + str(error)
            )
            try:
                send_notification("Configuration error", str(error))
            except Exception as exception:
                # Catch everything to prevent a crash
                logger.error("Error while sending a notification: " + str(exception))

            # There was an error, return early and don't restart
            return

        argv = [sys.executable] + sys.argv
        if "--no-spawn" not in argv:
            argv.append("--no-spawn")
        buf = io.BytesIO()
        try:
            pickle.dump(QtileState(self._qtile), buf, protocol=0)
        except:  # noqa: E722
            logger.error("Unable to pickle qtile state")
        argv = [s for s in argv if not s.startswith("--with-state")]
        argv.append("--with-state=" + buf.getvalue().decode())
        self._qtile._restart = (sys.executable, argv)
        self._qtile.stop()

    def cmd_spawn(self, cmd) -> int:
        """Run cmd in a shell.

        cmd may be a string, which is parsed by shlex.split, or a list (similar
        to subprocess.Popen).

        Examples
        ========

            spawn("firefox")

            spawn(["xterm", "-T", "Temporary terminal"])
        """
        return self._qtile.spawn(cmd)

    def cmd_status(self) -> str:
        """Return "OK" if Qtile is running"""
        return "OK"

    def cmd_sync(self) -> None:
        """Sync the X display. Should only be used for development"""
        self._qtile.conn.flush()

    def cmd_to_screen(self, n) -> None:
        """Warp focus to screen n, where n is a 0-based screen number

        Examples
        ========

            to_screen(0)
        """
        return self._qtile.focus_screen(n)

    def cmd_next_screen(self) -> None:
        """Move to next screen"""
        return self._qtile.focus_screen(
            (self._qtile.screens.index(self._qtile.current_screen) + 1)
            % len(self._qtile.screens)
        )

    def cmd_prev_screen(self) -> None:
        """Move to the previous screen"""
        return self._qtile.focus_screen(
            (self._qtile.screens.index(self._qtile.current_screen) - 1)
            % len(self._qtile.screens)
        )

    def cmd_windows(self) -> List[Dict]:
        """Return info for each client window"""
        return [
            i.info()
            for i in self._qtile.windows_map.values()
            if not isinstance(i, window.Internal)
        ]

    def cmd_internal_windows(self) -> List[Dict]:
        """Return info for each internal window (bars, for example)"""
        return [
            i.info()
            for i in self._qtile.windows_map.values()
            if isinstance(i, window.Internal)
        ]

    def cmd_qtile_info(self) -> Dict:
        """Returns a dictionary of info on the Qtile instance"""
        return {}

    def cmd_shutdown(self) -> None:
        """Quit Qtile"""
        self._qtile.stop()

    def cmd_switch_groups(self, groupa: str, groupb: str) -> None:
        """Switch position of groupa to groupb"""
        if groupa not in self._qtile.groups_map or groupb not in self._qtile.groups_map:
            return

        indexa = self._qtile.groups.index(self._qtile.groups_map[groupa])
        indexb = self._qtile.groups.index(self._qtile.groups_map[groupb])

        self._qtile.groups[indexa], self._qtile.groups[indexb] = (
            self._qtile.groups[indexb],
            self._qtile.groups[indexa],
        )
        hook.fire("setgroup")

        # update window _NET_WM_DESKTOP
        for group in (self._qtile.groups[indexa], self._qtile.groups[indexb]):
            for w in group.windows:
                w.group = group

    def cmd_findwindow(self, prompt: str = "window", widget: str = "prompt") -> None:
        """Launch prompt widget to find a window of the given name

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "window")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        mb = self._qtile.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(prompt, self._qtile.find_window, "window", strict_completer=True)

    def cmd_next_urgent(self) -> None:
        """Focus next window with urgent hint"""
        try:
            nxt = [w for w in self._qtile.windows_map.values() if w.urgent][0]
            nxt.group.cmd_toscreen()
            nxt.group.focus(nxt)
        except IndexError:
            pass  # no window had urgent set

    def cmd_togroup(self, prompt: str = "group", widget: str = "prompt") -> None:
        """Launch prompt widget to move current window to a given group

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "group")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        if not self._qtile.current_window:
            logger.warning("No window to move")
            return

        mb = self._qtile.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(
            prompt, self._qtile.move_to_group, "group", strict_completer=True
        )

    def cmd_switchgroup(self, prompt: str = "group", widget: str = "prompt") -> None:
        """Launch prompt widget to switch to a given group to the current screen

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "group")
        widget :
            Name of the prompt widget (default: "prompt")
        """

        def f(group):
            if group:
                try:
                    self._qtile.groups_map[group].cmd_toscreen()
                except KeyError:
                    logger.info("No group named '{0:s}' present.".format(group))

        mb = self._qtile.widgets_map.get(widget)
        if not mb:
            logger.warning("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(prompt, f, "group", strict_completer=True)

    def cmd_spawncmd(
        self, prompt: str = "spawn", widget: str = "prompt", command: str = "%s", complete: str = "cmd"
    ) -> None:
        """Spawn a command using a prompt widget, with tab-completion.

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "spawn: ").
        widget :
            Name of the prompt widget (default: "prompt").
        command :
            command template (default: "%s").
        complete :
            Tab completion function (default: "cmd")
        """

        def f(args):
            if args:
                self._qtile.cmd_spawn(command % args)

        try:
            mb = self._qtile.widgets_map[widget]
            mb.start_input(prompt, f, complete)
        except KeyError:
            logger.error("No widget named '{0:s}' present.".format(widget))

    def cmd_qtilecmd(
        self, prompt: str = "command", widget: str = "prompt", messenger: str = "xmessage"
    ) -> None:
        """Execute a Qtile command using the client syntax

        Tab completion aids navigation of the command tree

        Parameters
        ==========
        prompt :
            Text to display at the prompt (default: "command: ")
        widget :
            Name of the prompt widget (default: "prompt")
        messenger :
            Command to display output, set this to None to disable (default:
            "xmessage")
        """

        def f(cmd):
            if cmd:
                # c here is used in eval() below
                q = QtileCommandInterface(self._qtile)
                c = InteractiveCommandClient(q)  # noqa: F841
                try:
                    cmd_arg = str(cmd).split(" ")
                except AttributeError:
                    return
                cmd_len = len(cmd_arg)
                if cmd_len == 0:
                    logger.info("No command entered.")
                    return
                try:
                    result = eval(u"c.{0:s}".format(cmd))
                except (CommandError, CommandException, AttributeError) as err:
                    logger.error(err)
                    result = None
                if result is not None:
                    from pprint import pformat

                    message = pformat(result)
                    if messenger:
                        self._qtile.cmd_spawn(
                            '{0:s} "{1:s}"'.format(messenger, message)
                        )
                    logger.debug(result)

        mb = self._qtile.widgets_map[widget]
        if not mb:
            logger.error("No widget named {0:s} present.".format(widget))
            return
        mb.start_input(prompt, f, "qshell")

    def cmd_addgroup(self, group: str, label=None, layout=None, layouts=None) -> None:
        """Add a group with the given name"""
        return self._qtile.add_group(
            name=group, layout=layout, layouts=layouts, label=label
        )

    def cmd_delgroup(self, group: str) -> None:
        """Delete a group with the given name"""
        return self._qtile.delete_group(group)

    def cmd_add_rule(self, match_args, rule_args, min_priorty=False) -> None:
        """Add a dgroup rule, returns rule_id needed to remove it

        Parameters
        ==========
        match_args :
            config.Match arguments
        rule_args :
            config.Rule arguments
        min_priorty :
            If the rule is added with minimum prioriry (last) (default: False)
        """
        if not self._qtile.dgroups:
            logger.warning("No dgroups created")
            return

        match = Match(**match_args)
        rule = Rule(match, **rule_args)
        return self._qtile.dgroups.add_rule(rule, min_priorty)

    def cmd_remove_rule(self, rule_id) -> None:
        """Remove a dgroup rule by rule_id"""
        self._qtile.dgroups.remove_rule(rule_id)

    def cmd_run_external(self, full_path) -> str:
        """Run external Python script"""

        def format_error(path, e):
            s = """Can't call "main" from "{path}"\n\t{err_name}: {err}"""
            return s.format(path=path, err_name=e.__class__.__name__, err=e)

        module_name = os.path.splitext(os.path.basename(full_path))[0]
        dir_path = os.path.dirname(full_path)
        err_str = ""
        local_stdout = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = local_stdout

        try:
            module = _import_module(module_name, dir_path)
            module.main(self._qtile)
        except ImportError as e:
            err_str += format_error(full_path, e)
        except:  # noqa: E722
            exc_type, exc_value, exc_traceback = sys.exc_info()
            assert exc_type is not None
            err_str += traceback.format_exc()
            err_str += format_error(full_path, exc_type(exc_value))
        finally:
            sys.stdout = old_stdout
            local_stdout.close()

        return local_stdout.getvalue() + err_str

    def cmd_hide_show_bar(self, position: str = "all") -> None:
        """Toggle visibility of a given bar

        Parameters
        ==========
        position :
            one of: "top", "bottom", "left", "right", or "all" (default: "all")
        """
        if position in ["top", "bottom", "left", "right"]:
            bar = getattr(self._qtile.current_screen, position)
            if bar:
                bar.show(not bar.is_show())
                self._qtile.current_group.layout_all()
            else:
                logger.warning(
                    "Not found bar in position '%s' for hide/show." % position
                )
        elif position == "all":
            screen = self._qtile.current_screen
            is_show = None
            for bar in [screen.left, screen.right, screen.top, screen.bottom]:
                if bar:
                    if is_show is None:
                        is_show = not bar.is_show()
                    bar.show(is_show)
            if is_show is not None:
                self._qtile.current_group.layout_all()
            else:
                logger.warning("Not found bar for hide/show.")
        else:
            logger.error("Invalid position value:{0:s}".format(position))

    def cmd_get_state(self) -> str:
        """Get pickled state for restarting qtile"""
        buf = io.BytesIO()
        pickle.dump(QtileState(self._qtile), buf, protocol=0)
        state = buf.getvalue().decode()
        logger.debug("State =")
        logger.debug("".join(state.split("\n")))
        return state

    def cmd_tracemalloc_toggle(self) -> None:
        """Toggle tracemalloc status

        Running tracemalloc is required for qtile-top
        """
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        else:
            tracemalloc.stop()

    def cmd_tracemalloc_dump(self) -> Tuple[bool, str]:
        """Dump tracemalloc snapshot"""
        import tracemalloc

        if not tracemalloc.is_tracing():
            return False, "Trace not started"
        cache_directory = get_cache_dir()
        malloc_dump = os.path.join(cache_directory, "qtile_tracemalloc.dump")
        tracemalloc.take_snapshot().dump(malloc_dump)
        return True, malloc_dump

    def cmd_get_test_data(self):
        """
        Returns any content arbitrarily set in the self.test_data attribute.
        Useful in tests.
        """
        return self._qtile.test_data

    def cmd_run_extension(self, extension) -> None:
        """Run extensions"""
        extension.run()
