# -*- coding: utf-8 -*-
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

import copy
import glob
import os
import pickle
import string
import logging
from collections import deque

from . import base
from .. import bar, command, hook, pangocffi, utils, xcbq, xkeysyms


class NullCompleter(object):
    def __init__(self, qtile):
        self.qtile = qtile
        self.thisfinal = ""

    def actual(self):
        return self.thisfinal

    def reset(self):
        pass

    def complete(self, txt):
        return txt


class FileCompleter(object):
    def __init__(self, qtile, _testing=False):
        self._testing = _testing
        self.qtile = qtile
        self.thisfinal = None
        self.reset()

    def actual(self):
        return self.thisfinal

    def reset(self):
        self.lookup = None

    def complete(self, txt):
        """
        Returns the next completion for txt, or None if there is no completion.
        """
        if not self.lookup:
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


class QshCompleter(object):
    def __init__(self, qtile):
        self.qtile = qtile
        self.client = command.CommandRoot(self.qtile)
        self.thisfinal = None
        self.reset()

    def actual(self):
        return self.thisfinal

    def reset(self):
        self.lookup = None
        self.path = ''
        self.offset = -1

    def complete(self, txt):
        txt = txt.lower()
        if not self.lookup:
            self.lookup = []
            path = txt.split('.')[:-1]
            self.path = '.'.join(path)
            term = txt.split('.')[-1]
            if len(self.path) > 0:
                self.path += '.'

            contains_cmd = 'self.client.%s_contains' % self.path
            try:
                contains = eval(contains_cmd)
            except AttributeError:
                contains = []
            for obj in contains:
                if obj.lower().startswith(term):
                    self.lookup.append((obj, obj))

            commands_cmd = 'self.client.%scommands()' % self.path
            try:
                commands = eval(commands_cmd)
            except (command.CommandError, AttributeError):
                commands = []
            for cmd in commands:
                if cmd.lower().startswith(term):
                    self.lookup.append((cmd + '()', cmd + '()'))

            self.offset = -1
            self.lookup.append((term, term))

        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.thisfinal = self.path + ret[0]
        return self.path + ret[0]


class GroupCompleter(object):
    def __init__(self, qtile):
        self.qtile = qtile
        self.thisfinal = None
        self.lookup = None
        self.offset = None

    def actual(self):
        """
            Returns the current actual value.
        """
        return self.thisfinal

    def reset(self):
        self.lookup = None
        self.offset = -1

    def complete(self, txt):
        """
        Returns the next completion for txt, or None if there is no completion.
        """
        txt = txt.lower()
        if not self.lookup:
            self.lookup = []
            for group in self.qtile.groupMap.keys():
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


class WindowCompleter(object):
    def __init__(self, qtile):
        self.qtile = qtile
        self.thisfinal = None
        self.lookup = None
        self.offset = None

    def actual(self):
        """
            Returns the current actual value.
        """
        return self.thisfinal

    def reset(self):
        self.lookup = None
        self.offset = -1

    def complete(self, txt):
        """
        Returns the next completion for txt, or None if there is no completion.
        """
        if not self.lookup:
            self.lookup = []
            for wid, window in self.qtile.windowMap.items():
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


class CommandCompleter(object):
    DEFAULTPATH = "/bin:/usr/bin:/usr/local/bin"

    def __init__(self, qtile, _testing=False):
        """
        _testing: disables reloading of the lookup table
                  to make testing possible.
        """
        self.lookup = None
        self.offset = None
        self.thisfinal = None
        self._testing = _testing

    def actual(self):
        """
            Returns the current actual value.
        """
        return self.thisfinal

    def executable(self, fpath):
        return os.access(fpath, os.X_OK)

    def reset(self):
        self.lookup = None
        self.offset = -1

    def complete(self, txt):
        """
        Returns the next completion for txt, or None if there is no completion.
        """
        if not self.lookup:
            if not self._testing:
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
                    for didx, d in enumerate(dirs):
                        try:
                            for cmd in glob.glob(os.path.join(d, "%s*" % txt)):
                                if self.executable(cmd):
                                    self.lookup.append(
                                        (
                                            os.path.basename(cmd),
                                            cmd
                                        ),
                                    )
                        except OSError:
                            pass
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
    """
        A widget that prompts for user input. Input should be started using the
        .startInput method on this class.
    """
    completers = {
        "file": FileCompleter,
        "qsh": QshCompleter,
        "cmd": CommandCompleter,
        "group": GroupCompleter,
        "window": WindowCompleter,
        None: NullCompleter
    }
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [("cursor", True, "Show a cursor"),
                ("cursorblink", 0.5, "Cursor blink rate. 0 to disable."),
                ("cursor_color", "bef098",
                 "Color for the cursor and text over it."),
                ("prompt", "{prompt}: ", "Text displayed at the prompt"),
                ("record_history", True, "Keep a record of executed commands"),
                ("max_history", 100,
                 "Commands to keep in history. 0 for no limit."),
                ("bell_style", "audible",
                 "Alert at the begin/end of the command history. " +
                 "Posible values: 'audible', 'visual' and None."),
                ("visual_bell_color", "ff0000",
                 "Color for the visual bell (changes prompt background)."),
                ("visual_bell_time", 0.2,
                 "Visual bell duration (in seconds).")]

    def __init__(self, name="prompt", **config):
        base._TextBox.__init__(self, "", bar.CALCULATED, **config)
        self.add_defaults(Prompt.defaults)
        self.name = name
        self.active = False
        self.completer = None
        # Define key handlers (action to do when hit an specific key)
        self.keyhandlers = {
            xkeysyms.keysyms['Tab']: self._trigger_complete,
            xkeysyms.keysyms['BackSpace']: self._delete_char(),
            xkeysyms.keysyms['Delete']: self._delete_char(False),
            xkeysyms.keysyms['KP_Delete']: self._delete_char(False),
            xkeysyms.keysyms['Escape']: self._unfocus,
            xkeysyms.keysyms['Return']: self._send_cmd,
            xkeysyms.keysyms['KP_Enter']: self._send_cmd,
            xkeysyms.keysyms['Up']: self._get_prev_cmd,
            xkeysyms.keysyms['KP_Up']: self._get_prev_cmd,
            xkeysyms.keysyms['Down']: self._get_next_cmd,
            xkeysyms.keysyms['KP_Down']: self._get_next_cmd,
            xkeysyms.keysyms['Left']: self._move_cursor(),
            xkeysyms.keysyms['KP_Left']: self._move_cursor(),
            xkeysyms.keysyms['Right']: self._move_cursor("right"),
            xkeysyms.keysyms['KP_Right']: self._move_cursor("right"),
        }
        printables = [int(hex(x), 16) for x in range(127)]
        printables = {x: self._write_char for x in printables if
                      chr(x) in string.printable}
        self.keyhandlers.update(printables)
        if self.bell_style == "visual":
            self.original_background = self.background
        # If history record is on, get saved history or create history record
        if self.record_history:
            self.history_path = os.path.expanduser('~/.qtile_history')
            if os.path.exists(self.history_path):
                with open(self.history_path, 'rb') as f:
                    try:
                        self.history = pickle.load(f)
                    except:
                        # unfortunately, pickle doesn't wrap its errors, so we
                        # can't detect what's a pickle error and what's not.
                        log = logging.getLogger('qtile')
                        log.exception("failed to load prompt history")
                        self.history = {x: deque(maxlen=self.max_history)
                                        for x in self.completers if x}
                    if self.max_history != \
                       self.history[list(self.history)[0]].maxlen:
                        self.history = {x: deque(copy.copy(self.history[x]),
                                                 self.max_history)
                                        for x in self.completers if x}
            else:
                self.history = {x: deque(maxlen=self.max_history)
                                for x in self.completers if x}

    def _configure(self, qtile, bar):
        self.markup = True
        base._TextBox._configure(self, qtile, bar)

        def f(win):
            if self.active and not win == self.bar.window:
                self._unfocus()

        hook.subscribe.client_focus(f)

    def startInput(self, prompt, callback,
                   complete=None, strict_completer=False):
        """
            complete: Tab-completion. Can be None, "cmd", "file", "group",
            "qsh" or "window".

            Displays a prompt and starts to take one line of keyboard input
            from the user. When done, calls the callback with the input string
            as argument. If history record is enabled, also allows to browse
            between previous commands with ↑ and ↓, and execute them
            (untouched or modified). When historial is exhausted, fires an
            alert. It tries to mimic, in some way, the shell behavior.

            prompt = text displayed at the prompt, e.g. "spawn: "
            callback = function to call with returned value.
            complete = completer to use.
            strict_completer = When True the return value wil be the exact
                               completer result where available.
        """

        if self.cursor and self.cursorblink and not self.active:
            self.timeout_add(self.cursorblink, self._blink)
        self.display = self.prompt.format(prompt=prompt)
        self.display = pangocffi.markup_escape_text(self.display)
        self.active = True
        self.userInput = ""
        self.archivedInput = ""
        self.show_cursor = self.cursor
        self.cursor_position = 0
        self.callback = callback
        self.completer = self.completers[complete](self.qtile)
        self.strict_completer = strict_completer
        self._update()
        self.bar.widget_grab_keyboard(self)
        if self.record_history:
            self.completer_history = self.history[complete]
            self.position = len(self.completer_history)

    def calculate_length(self):
        if self.text:
            width = min(
                self.layout.width,
                self.bar.width
            ) + self.actual_padding * 2
            return width
        else:
            return 0

    def _blink(self):
        self.show_cursor = not self.show_cursor
        self._update()
        if self.active:
            self.timeout_add(self.cursorblink, self._blink)

    def _highlight_text(self, text):
        color = utils.hex(self.cursor_color)
        text = '<span foreground="{}">{}</span>'.format(color, text)
        if self.show_cursor:
            text = '<u>{}</u>'.format(text)
        return text

    def _update(self):
        if self.active:
            self.text = self.archivedInput or self.userInput
            cursor = pangocffi.markup_escape_text(" ")
            if self.cursor_position < len(self.text):
                txt1 = self.text[:self.cursor_position]
                txt2 = self.text[self.cursor_position]
                txt3 = self.text[self.cursor_position + 1:]
                for text in (txt1, txt2, txt3):
                    text = pangocffi.markup_escape_text(text)
                txt2 = self._highlight_text(txt2)
                self.text = "{}{}{}{}".format(txt1, txt2, txt3, cursor)
            else:
                self.text = pangocffi.markup_escape_text(self.text)
                self.text = self.text + self._highlight_text(cursor)
            self.text = self.display + self.text
        else:
            self.text = ""
        self.bar.draw()

    def _trigger_complete(self):
        # Trigger the autocompletion in user input
        self.userInput = self.completer.complete(self.userInput)
        self.cursor_position = len(self.userInput)

    def _history_to_input(self):
        # Move actual command (when exploring history) to user input and update
        # history position (right after the end)
        if self.archivedInput:
            self.userInput = self.archivedInput
            self.archivedInput = ""
            self.position = len(self.completer_history)

    def _insert_before_cursor(self, charcode):
        # Insert a caracter (given their charcode) in input, before the cursor
        txt1 = self.userInput[:self.cursor_position]
        txt2 = self.userInput[self.cursor_position:]
        self.userInput = txt1 + chr(charcode) + txt2
        self.cursor_position += 1

    def _delete_char(self, backspace=True):
        # Return a function that deletes character from the input text.
        # If backspace is True, function will emulate backspace, else Delete.
        def f():
            self._history_to_input()
            step = -1 if backspace else 0
            if not backspace and self.cursor_position == len(self.userInput):
                self._alert()
            elif len(self.userInput) > 0 and self.cursor_position + step > -1:
                txt1 = self.userInput[:self.cursor_position + step]
                txt2 = self.userInput[self.cursor_position + step + 1:]
                self.userInput = txt1 + txt2
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
            self.userInput = self.actual_value or self.userInput
            del self.actual_value
        self._history_to_input()
        if self.userInput:
            # If history record is activated, also save command in history
            if self.record_history:
                self.completer_history.append(self.userInput)
                if self.position < self.max_history:
                    self.position += 1
                with open(self.history_path, mode='wb') as f:
                    pickle.dump(self.history, f, protocol=2)
            self.callback(self.userInput)

    def _alert(self):
        # Fire an alert (audible or visual), if bell style is not None.
        if self.bell_style == "audible":
            self.qtile.conn.conn.core.Bell(0)
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
                self.archivedInput = self.completer_history[self.position]
                self.cursor_position = len(self.archivedInput)

    def _get_next_cmd(self):
        # Get the next command in history.
        # If the last command was already reached, ring system bell.
        if self.record_history:
            if self.position == len(self.completer_history):
                self._alert()
            elif self.position < len(self.completer_history):
                self.position += 1
                if self.position == len(self.completer_history):
                    self.archivedInput = ""
                else:
                    self.archivedInput = self.completer_history[self.position]
                self.cursor_position = len(self.archivedInput)

    def _cursor_to_left(self):
        # Move cursor to left, if possible
        if self.cursor_position:
            self.cursor_position -= 1
        else:
            self._alert()

    def _cursor_to_right(self):
        # move cursor to right, if possible
        command = self.archivedInput or self.userInput
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
            if k != xkeysyms.keysyms['Tab']:
                self.actual_value = self.completer.actual()
                self.completer.reset()
            return self.keyhandlers[k]

    def handle_KeyPress(self, e):
        """KeyPress handler for the minibuffer.

        Currently only supports ASCII characters.
        """
        state = e.state & ~(self.qtile.numlockMask)
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, state)
        handle_key = self._get_keyhandler(keysym)
        if handle_key:
            handle_key()
            del self.key
        self._update()

    def cmd_fake_keypress(self, key):
        class Dummy(object):
            pass
        d = Dummy()
        keysym = xcbq.keysyms[key]
        d.detail = self.qtile.conn.keysym_to_keycode(keysym)
        d.state = 0
        self.handle_KeyPress(d)

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return dict(
            name=self.name,
            width=self.width,
            text=self.text,
            active=self.active,
        )
