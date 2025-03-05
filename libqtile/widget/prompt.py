# Copyright (c) 2010-2011 Aldo Cortesi
# Copyright (c) 2010 Philip Kranz
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2011-2012 roger
# Copyright (c) 2011-2012, 2014 Tycho Andersen
# Copyright (c) 2012 Dustin Lacewell
# Copyright (c) 2012 Laurie Clark-Michalek
# Copyright (c) 2012-2014 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (C) 2015, Juan Riquelme González
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

from __future__ import annotations

import abc
import glob
import os
import pickle
import string
from collections import deque

from libqtile import hook, pangocffi, utils
from libqtile.command.base import CommandObject, SelectError, expose_command
from libqtile.command.client import InteractiveCommandClient
from libqtile.command.interface import CommandError, QtileCommandInterface
from libqtile.log_utils import logger
from libqtile.widget import base


class AbstractCompleter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, qtile: CommandObject) -> None:
        pass

    @abc.abstractmethod
    def actual(self) -> str | None:
        pass

    @abc.abstractmethod
    def reset(self) -> None:
        pass

    @abc.abstractmethod
    def complete(self, txt: str, aliases: dict[str, str] | None = None) -> str:
        """
        Perform the requested completion on the given text.

        The completer can optionally support aliases, which map strings to commands. The
        completer should include the aliases in the completion results.
        """
        # pragma: no cover


class NullCompleter(AbstractCompleter):
    def __init__(self, qtile) -> None:
        self.qtile = qtile

    def actual(self) -> str:
        return ""

    def reset(self) -> None:
        pass

    def complete(self, txt: str, _aliases: dict[str, str] | None = None) -> str:
        return txt


class FileCompleter(AbstractCompleter):
    def __init__(self, qtile, _testing=False) -> None:
        self._testing = _testing
        self.qtile = qtile
        self.thisfinal = None  # type: str | None
        self.lookup = None  # type: list[tuple[str, str]] | None
        self.reset()

    def actual(self) -> str | None:
        return self.thisfinal

    def reset(self) -> None:
        self.lookup = None

    def complete(self, txt: str, _aliases: dict[str, str] | None = None) -> str:
        """Returns the next completion for txt, or None if there is no completion"""
        if self.lookup is None:
            self.lookup = []
            if txt == "" or txt[0] not in "~/":
                txt = "~/" + txt
            path = os.path.expanduser(txt)
            if os.path.isdir(path):
                files = glob.glob(os.path.join(path, "*"))
                prefix = txt
            else:
                files = glob.glob(path + "*")
                prefix = os.path.dirname(txt)
                prefix = prefix.rstrip("/") or "/"
            for f in files:
                display = os.path.join(prefix, os.path.basename(f))
                if os.path.isdir(f):
                    display += "/"
                self.lookup.append((display, f))
                self.lookup.sort()
            self.offset = -1
            self.lookup.append((txt, txt))
        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = ret[1]
        return ret[0]


class QshCompleter(AbstractCompleter):
    def __init__(self, qtile: CommandObject) -> None:
        q = QtileCommandInterface(qtile)
        self.client = InteractiveCommandClient(q)
        self.thisfinal = None  # type: str | None
        self.reset()

    def actual(self) -> str | None:
        return self.thisfinal

    def reset(self) -> None:
        self.lookup = None  # type: list[tuple[str, str]] | None
        self.path = ""
        self.offset = -1

    def complete(self, txt: str, _aliases: dict[str, str] | None = None) -> str:
        txt = txt.lower()
        if self.lookup is None:
            self.lookup = []
            path = txt.split(".")[:-1]
            self.path = ".".join(path)
            term = txt.split(".")[-1]
            if len(self.path) > 0:
                self.path += "."

            contains_cmd = f"self.client.{self.path}_contains"
            try:
                contains = eval(contains_cmd)
            except AttributeError:
                contains = []
            for obj in contains:
                if obj.lower().startswith(term):
                    self.lookup.append((obj, obj))

            commands_cmd = f"self.client.{self.path}commands()"
            try:
                commands = eval(commands_cmd)
            except (CommandError, AttributeError):
                commands = []
            for cmd in commands:
                if cmd.lower().startswith(term):
                    self.lookup.append((cmd + "()", cmd + "()"))

            self.offset = -1
            self.lookup.append((term, term))

        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = self.path + ret[0]
        return self.path + ret[0]


class GroupCompleter(AbstractCompleter):
    def __init__(self, qtile: CommandObject) -> None:
        self.qtile = qtile
        self.thisfinal = None  # type: str | None
        self.lookup = None  # type: list[tuple[str, str]] | None
        self.offset = -1

    def actual(self) -> str | None:
        """Returns the current actual value"""
        return self.thisfinal

    def reset(self) -> None:
        self.lookup = None
        self.offset = -1

    def complete(self, txt: str, _aliases: dict[str, str] | None = None) -> str:
        """Returns the next completion for txt, or None if there is no completion"""
        txt = txt.lower()
        if not self.lookup:
            self.lookup = []
            for group in self.qtile.groups_map.keys():
                if group.lower().startswith(txt):
                    self.lookup.append((group, group))

            self.lookup.sort()
            self.offset = -1
            self.lookup.append((txt, txt))

        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = ret[1]
        return ret[0]


class WindowCompleter(AbstractCompleter):
    def __init__(self, qtile: CommandObject) -> None:
        self.qtile = qtile
        self.thisfinal = None  # type: str | None
        self.lookup = None  # type: list[tuple[str, str]] | None
        self.offset = -1

    def actual(self) -> str | None:
        """Returns the current actual value"""
        return self.thisfinal

    def reset(self) -> None:
        self.lookup = None
        self.offset = -1

    def complete(self, txt: str, _aliases: dict[str, str] | None = None) -> str:
        """Returns the next completion for txt, or None if there is no completion"""
        if self.lookup is None:
            self.lookup = []
            for wid, window in self.qtile.windows_map.items():
                if window.group and window.name.lower().startswith(txt):
                    self.lookup.append((window.name, wid))

            self.lookup.sort()
            self.offset = -1
            self.lookup.append((txt, txt))

        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = ret[1]
        return ret[0]


class CommandCompleter:
    """
    Parameters
    ==========
    _testing :
        disables reloading of the lookup table to make testing possible.
    """

    DEFAULTPATH = "/bin:/usr/bin:/usr/local/bin"

    def __init__(self, qtile, _testing=False):
        self.lookup = None  # type: list[tuple[str, str]] | None
        self.offset = -1
        self.thisfinal = None  # type: str | None
        self._testing = _testing

    def actual(self) -> str | None:
        """Returns the current actual value"""
        return self.thisfinal

    def executable(self, fpath: str):
        return os.access(fpath, os.X_OK)

    def reset(self) -> None:
        self.lookup = None
        self.offset = -1

    def complete(self, txt: str, aliases: dict[str, str] | None = None) -> str:
        """Returns the next completion for txt, or None if there is no completion"""
        if self.lookup is None:
            # Lookup is a set of (display value, actual value) tuples.
            self.lookup = []
            if txt and txt[0] in "~/":
                path = os.path.expanduser(txt)
                if os.path.isdir(path):
                    files = glob.glob(os.path.join(path, "*"))
                    prefix = txt
                else:
                    files = glob.glob(path + "*")
                    prefix = os.path.dirname(txt)
                prefix = prefix.rstrip("/") or "/"
                for f in files:
                    if self.executable(f):
                        display = os.path.join(prefix, os.path.basename(f))
                        if os.path.isdir(f):
                            display += "/"
                        self.lookup.append((display, f))
            else:
                dirs = os.environ.get("PATH", self.DEFAULTPATH).split(":")
                for d in dirs:
                    try:
                        d = os.path.expanduser(d)
                        for cmd in glob.iglob(os.path.join(d, f"{txt}*")):
                            if self.executable(cmd):
                                self.lookup.append(
                                    (os.path.basename(cmd), cmd),
                                )
                    except OSError:
                        pass

            if aliases:
                for alias in aliases:
                    if alias.startswith(txt):
                        self.lookup.append((alias, aliases[alias]))

            self.lookup.sort()
            self.offset = -1
            self.lookup.append((txt, txt))
        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = ret[1]
        return ret[0]


class Prompt(base._TextBox):
    """A widget that prompts for user input

    Input should be started using the ``.start_input()`` method on this class.
    """

    completers = {
        "file": FileCompleter,
        "qshell": QshCompleter,
        "cmd": CommandCompleter,
        "group": GroupCompleter,
        "window": WindowCompleter,
        None: NullCompleter,
    }

    defaults = [
        ("cursor", True, "Show a cursor"),
        ("cursorblink", 0.5, "Cursor blink rate. 0 to disable."),
        ("cursor_color", "bef098", "Color for the cursor and text over it."),
        ("prompt", "{prompt}: ", "Text displayed at the prompt"),
        ("record_history", True, "Keep a record of executed commands"),
        ("max_history", 100, "Commands to keep in history. 0 for no limit."),
        ("ignore_dups_history", False, "Don't store duplicates in history"),
        (
            "bell_style",
            "audible",
            "Alert at the begin/end of the command history. "
            + "Possible values: 'audible' (X11 only), 'visual' and None.",
        ),
        ("visual_bell_color", "ff0000", "Color for the visual bell (changes prompt background)."),
        ("visual_bell_time", 0.2, "Visual bell duration (in seconds)."),
    ]

    def __init__(self, **config) -> None:
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(Prompt.defaults)
        self.active = False
        self.completer = None  # type: AbstractCompleter | None
        self.aliases: dict[str, str] | None = None

        # If history record is on, get saved history or create history record
        if self.record_history:
            self.history_path = os.path.join(utils.get_cache_dir(), "prompt_history")
            if os.path.exists(self.history_path):
                with open(self.history_path, "rb") as f:
                    try:
                        self.history = pickle.load(f)
                        if self.ignore_dups_history:
                            self._dedup_history()
                    except:  # noqa: E722
                        # unfortunately, pickle doesn't wrap its errors, so we
                        # can't detect what's a pickle error and what's not.
                        logger.exception("failed to load prompt history")
                        self.history = {
                            x: deque(maxlen=self.max_history) for x in self.completers
                        }

                    # self.history of size does not match.
                    if len(self.history) != len(self.completers):
                        self.history = {
                            x: deque(maxlen=self.max_history) for x in self.completers
                        }

                    if self.max_history != self.history[list(self.history)[0]].maxlen:
                        self.history = {
                            x: deque(self.history[x], self.max_history) for x in self.completers
                        }
            else:
                self.history = {x: deque(maxlen=self.max_history) for x in self.completers}

    def _configure(self, qtile, bar) -> None:
        self.markup = True
        base._TextBox._configure(self, qtile, bar)

        def f(win):
            if self.active and not win == self.bar.window:
                self._unfocus()

        def prevent_focus_steal(group, win):
            if self.active:
                win.can_steal_focus = False

        hook.subscribe.group_window_add(prevent_focus_steal)
        hook.subscribe.client_focus(f)

        # Define key handlers (action to do when a specific key is hit)
        keyhandlers = {
            "Tab": self._trigger_complete,
            "BackSpace": self._delete_char(),
            "Delete": self._delete_char(False),
            "KP_Delete": self._delete_char(False),
            "Escape": self._unfocus,
            "Return": self._send_cmd,
            "KP_Enter": self._send_cmd,
            "Up": self._get_prev_cmd,
            "KP_Up": self._get_prev_cmd,
            "Down": self._get_next_cmd,
            "KP_Down": self._get_next_cmd,
            "Left": self._move_cursor(),
            "KP_Left": self._move_cursor(),
            "Right": self._move_cursor("right"),
            "KP_Right": self._move_cursor("right"),
        }
        self.keyhandlers = {qtile.core.keysym_from_name(k): v for k, v in keyhandlers.items()}
        printables = {x: self._write_char for x in range(127) if chr(x) in string.printable}
        self.keyhandlers.update(printables)
        self.tab = qtile.core.keysym_from_name("Tab")

        self.bell_style: str
        if self.bell_style == "audible" and qtile.core.name != "x11":
            self.bell_style = "visual"
            logger.warning("Prompt widget only supports audible bell under X11")
        if self.bell_style == "visual":
            self.original_background = self.background

    def start_input(
        self,
        prompt,
        callback,
        complete=None,
        strict_completer=False,
        allow_empty_input=False,
        aliases: dict[str, str] | None = None,
    ) -> None:
        """Run the prompt

        Displays a prompt and starts to take one line of keyboard input from
        the user. When done, calls the callback with the input string as
        argument. If history record is enabled, also allows to browse between
        previous commands with ↑ and ↓, and execute them (untouched or
        modified). When history is exhausted, fires an alert. It tries to
        mimic, in some way, the shell behavior.

        Parameters
        ==========
        complete :
            Tab-completion. Can be None, "cmd", "file", "group", "qshell" or
            "window".
        prompt :
            text displayed at the prompt, e.g. "spawn: "
        callback :
            function to call with returned value.
        complete :
            completer to use.
        strict_completer :
            When True the return value wil be the exact completer result where
            available.
        allow_empty_input :
            When True, an empty value will still call the callback function
        aliases :
            Dictionary mapping aliases to commands. If the entered command is a key in
            this dict, the command it maps to will be executed instead.
        """

        if self.cursor and self.cursorblink and not self.active:
            self.timeout_add(self.cursorblink, self._blink)
        self.display = self.prompt.format(prompt=prompt)
        self.display = pangocffi.markup_escape_text(self.display)
        self.active = True
        self.user_input = ""
        self.archived_input = ""
        self.show_cursor = self.cursor
        self.cursor_position = 0
        self.callback = callback
        self.aliases = aliases
        self.completer = self.completers[complete](self.qtile)
        self.strict_completer = strict_completer
        self.allow_empty_input = allow_empty_input
        self._update()
        self.bar.widget_grab_keyboard(self)
        if self.record_history:
            self.completer_history = self.history[complete]
            self.position = len(self.completer_history)

    def calculate_length(self) -> int:
        if self.text:
            width = min(self.layout.width, self.bar.width) + self.actual_padding * 2
            return width
        else:
            return 0

    def _blink(self) -> None:
        self.show_cursor = not self.show_cursor
        self._update()
        if self.active:
            self.timeout_add(self.cursorblink, self._blink)

    def _highlight_text(self, text) -> str:
        color = utils.hex(self.cursor_color)
        text = f'<span foreground="{color}">{text}</span>'
        if self.show_cursor:
            text = f"<u>{text}</u>"
        return text

    def _update(self) -> None:
        if self.active:
            self.text = self.archived_input or self.user_input
            cursor = pangocffi.markup_escape_text(" ")
            if self.cursor_position < len(self.text):
                txt1 = self.text[: self.cursor_position]
                txt2 = self.text[self.cursor_position]
                txt3 = self.text[self.cursor_position + 1 :]
                for text in (txt1, txt2, txt3):
                    text = pangocffi.markup_escape_text(text)
                txt2 = self._highlight_text(txt2)
                self.text = f"{txt1}{txt2}{txt3}{cursor}"
            else:
                self.text = pangocffi.markup_escape_text(self.text)
                self.text += self._highlight_text(cursor)
            self.text = self.display + self.text
        else:
            self.text = ""
        self.bar.draw()

    def _trigger_complete(self) -> None:
        # Trigger the auto completion in user input
        assert self.completer is not None
        self.user_input = self.completer.complete(self.user_input, self.aliases)
        self.cursor_position = len(self.user_input)

    def _history_to_input(self) -> None:
        # Move actual command (when exploring history) to user input and update
        # history position (right after the end)
        if self.archived_input:
            self.user_input = self.archived_input
            self.archived_input = ""
            self.position = len(self.completer_history)

    def _insert_before_cursor(self, charcode) -> None:
        # Insert a character (given their charcode) in input, before the cursor
        txt1 = self.user_input[: self.cursor_position]
        txt2 = self.user_input[self.cursor_position :]
        self.user_input = txt1 + chr(charcode) + txt2
        self.cursor_position += 1

    def _delete_char(self, backspace=True):
        # Return a function that deletes character from the input text.
        # If backspace is True, function will emulate backspace, else Delete.
        def f():
            self._history_to_input()
            step = -1 if backspace else 0
            if not backspace and self.cursor_position == len(self.user_input):
                self._alert()
            elif len(self.user_input) > 0 and self.cursor_position + step > -1:
                txt1 = self.user_input[: self.cursor_position + step]
                txt2 = self.user_input[self.cursor_position + step + 1 :]
                self.user_input = txt1 + txt2
                if step:
                    self.cursor_position += step
            else:
                self._alert()

        return f

    def _write_char(self):
        # Add pressed (legal) char key to user input.
        # No LookupString in XCB... oh, the shame! Unicode users beware!
        self._history_to_input()
        self._insert_before_cursor(self.key)

    def _unfocus(self):
        # Remove focus from the widget
        self.active = False
        self._update()
        self.bar.widget_ungrab_keyboard()

    def _send_cmd(self):
        # Send the prompted text for execution
        self._unfocus()
        if self.strict_completer:
            self.user_input = self.actual_value or self.user_input
            del self.actual_value
        self._history_to_input()
        if self.user_input or self.allow_empty_input:
            # If history record is activated, also save command in history
            if self.record_history:
                # ensure no dups in history
                if self.ignore_dups_history and (self.user_input in self.completer_history):
                    self.completer_history.remove(self.user_input)
                    self.position -= 1

                self.completer_history.append(self.user_input)

                if self.position < self.max_history:
                    self.position += 1
                os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
                with open(self.history_path, mode="wb") as f:
                    pickle.dump(self.history, f, protocol=2)
            self.callback(self.user_input)

    def _alert(self):
        # Fire an alert (audible or visual), if bell style is not None.
        if self.bell_style == "audible":
            self.qtile.core.conn.conn.core.Bell(0)
        elif self.bell_style == "visual":
            self.background = self.visual_bell_color
            self.timeout_add(self.visual_bell_time, self._stop_visual_alert)

    def _stop_visual_alert(self):
        self.background = self.original_background
        self._update()

    def _get_prev_cmd(self):
        # Get the previous command in history.
        # If there isn't more previous commands, ring system bell
        if self.record_history:
            if not self.position:
                self._alert()
            else:
                self.position -= 1
                self.archived_input = self.completer_history[self.position]
                self.cursor_position = len(self.archived_input)

    def _get_next_cmd(self):
        # Get the next command in history.
        # If the last command was already reached, ring system bell.
        if self.record_history:
            if self.position == len(self.completer_history):
                self._alert()
            elif self.position < len(self.completer_history):
                self.position += 1
                if self.position == len(self.completer_history):
                    self.archived_input = ""
                else:
                    self.archived_input = self.completer_history[self.position]
                self.cursor_position = len(self.archived_input)

    def _cursor_to_left(self):
        # Move cursor to left, if possible
        if self.cursor_position:
            self.cursor_position -= 1
        else:
            self._alert()

    def _cursor_to_right(self):
        # move cursor to right, if possible
        command = self.archived_input or self.user_input
        if self.cursor_position < len(command):
            self.cursor_position += 1
        else:
            self._alert()

    def _move_cursor(self, direction="left"):
        # Move the cursor to left or right, according to direction
        if direction == "left":
            return self._cursor_to_left
        elif direction == "right":
            return self._cursor_to_right

    def _get_keyhandler(self, k):
        # Return the action (a function) to do according the pressed key (k).
        self.key = k
        if k in self.keyhandlers:
            if k != self.tab:
                self.actual_value = self.completer.actual()
                self.completer.reset()
            return self.keyhandlers[k]

    def process_key_press(self, keysym: int):
        """Key press handler for the minibuffer.

        Currently only supports ASCII characters.
        """
        handle_key = self._get_keyhandler(keysym)

        if handle_key:
            handle_key()
            del self.key
        self._update()

    @expose_command()
    def fake_keypress(self, key: str) -> None:
        self.process_key_press(self.qtile.core.keysym_from_name(key))

    @expose_command()
    def info(self):
        """Returns a dictionary of info for this object"""
        return dict(
            name=self.name,
            width=self.width,
            text=self.text,
            active=self.active,
        )

    @expose_command()
    def exec_general(self, prompt, object_name, cmd_name, selector=None, completer=None):
        """
        Execute a cmd of any object. For example layout, group, window, widget
        , etc with a string that is obtained from start_input.

        Parameters
        ==========
        prompt :
            Text displayed at the prompt.
        object_name :
            Name of a object in Qtile. This string has to be 'layout', 'widget',
            'bar', 'window' or 'screen'.
        cmd_name :
            Execution command of selected object using object_name and selector.
        selector :
            This value select a specific object within a object list that is
            obtained by object_name.
            If this value is None, current object is selected. e.g. current layout,
            current window and current screen.
        completer:
            Completer to use.

        config example:
            Key([alt, 'shift'], 'a',
                lazy.widget['prompt'].exec_general(
                    'section(add)',
                    'layout',
                    'add_section'))
        """
        try:
            obj = self.qtile.select([(object_name, selector)])
        except SelectError:
            logger.warning("cannot select a object")
            return
        cmd = obj.command(cmd_name)
        if not cmd:
            logger.warning("command not found")
            return

        def f(args):
            if args:
                cmd(args)

        self.start_input(prompt, f, completer)

    def _dedup_history(self):
        """Filter the history deque, clearing all duplicate values."""
        self.history = {x: self._dedup_deque(self.history[x]) for x in self.completers}

    def _dedup_deque(self, dq):
        return deque(_LastUpdatedOrdereddict.fromkeys(dq))


class _LastUpdatedOrdereddict(dict):
    """Store items in the order the keys were last added."""

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        super().__setitem__(key, value)
