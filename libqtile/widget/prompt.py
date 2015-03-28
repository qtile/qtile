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
from collections import deque

from . import base
from .. import bar, command, hook, xcbq, xkeysyms


class NullCompleter:
    def __init__(self, qtile):
        self.qtile = qtile
        self.thisfinal = ""

    def actual(self):
        return self.thisfinal

    def reset(self):
        pass

    def complete(self, txt):
        return txt


class FileCompleter:
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


class QshCompleter:
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


class GroupCompleter:
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


class WindowCompleter:
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


class CommandCompleter:
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
    defaults = [("cursorblink", 0.5, "Cursor blink rate. 0 to disable."),
                ("prompt", "{prompt}: ", "Text displayed at the prompt"),
                ("record_history", True, "Keep a record of executed commands"),
                ("max_history", 100,
                 "Commands to keep in history. 0 for no limit."),
                ("bell_style", "audible",
                 "Alert at the begin/end of the command history. " +
                 "Posible values: 'audible', 'visual' and None."),
                ("visual_bell_color", "ff0000",
                 "Color for the visual bell (changes text prompt color)."),
                ("visual_bell_time", 0.4,
                 "Visual bell duration (in seconds).")]

    def __init__(self, name="prompt", **config):
        base._TextBox.__init__(self, "", bar.CALCULATED, **config)
        self.add_defaults(Prompt.defaults)
        self.name = name
        self.active = False
        self.blink = False
        self.completer = None
        # If history record is on, get saved history or create history record
        if self.record_history:
            self.history_path = os.path.expanduser('~/.qtile_history')
            if os.path.exists(self.history_path):
                with open(self.history_path, 'rb') as f:
                    self.history = pickle.load(f)
                    if self.max_history != \
                       self.history[list(self.history)[0]].maxlen:
                        self.history = {x: deque(copy.copy(self.history[x]),
                                                 self.max_history)
                                        for x in self.completers if x}
            else:
                self.history = {x: deque(maxlen=self.max_history)
                                for x in self.completers if x}

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

        def f(win):
            if self.active and not self.bar.window == win:
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

        if self.cursorblink and not self.active:
            self.timeout_add(self.cursorblink, self._blink)
        self.display = self.prompt.format(prompt=prompt)
        self.active = True
        self.userInput = ""
        self.archivedInput = ""
        self.callback = callback
        self.completer = self.completers[complete](self.qtile)
        self.strict_completer = strict_completer
        self._update()
        self.bar.widget_grab_keyboard(self)
        if self.record_history:
            self.completer_history = self.history[complete]
            self.position = len(self.completer_history)

    def _calculate_real_width(self):
        if self.blink:
            return min(
                self.layout.width,
                self.bar.width
            ) + self.actual_padding * 2
        else:
            _text = self.text
            self.text = _text + "_"
            width = min(
                self.layout.width,
                self.bar.width
            ) + self.actual_padding * 2
            self.text = _text
            return width

    def calculate_length(self):
        if self.text:
            return self._calculate_real_width()
        else:
            return 0

    def _blink(self):
        self.blink = not self.blink
        self._update()
        if self.active:
            self.timeout_add(self.cursorblink, self._blink)

    def _update(self):
        if self.active:
            if self.archivedInput:
                self.text = "%s%s" % (self.display, self.archivedInput)
            else:
                self.text = "%s%s" % (self.display, self.userInput)
            if self.blink:
                self.text = self.text + "_"
            else:
                self.text = self.text
        else:
            self.text = ""
        self.bar.draw()

    def _trigger_complete(self):
        # Trigger the autocompletion in user input
        self.userInput = self.completer.complete(self.userInput)

    def _history_to_input(self):
        # Move actual command (when exploring history) to user input and update
        # history position (right after the end)
        if self.archivedInput:
            self.userInput = self.archivedInput
            self.archivedInput = ""
            self.position = len(self.completer_history)

    def _write_char(self):
        # Add pressed (legal) char key to user input.
        # No LookupString in XCB... oh, the shame! Unicode users beware!
        self._history_to_input()
        self.userInput += chr(self.key)
        del self.key

    def _backspace(self):
        # Delete the last char from user input
        self._history_to_input()
        if len(self.userInput) > 0:
            self.userInput = self.userInput[:-1]

    def _unfocus(self):
        # Remove focus from the widget
        self.active = False
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
            self.layout.colour = self.visual_bell_color
            self.timeout_add(self.visual_bell_time, self._stop_visual_alert)

    def _stop_visual_alert(self):
        self.layout.colour = self.foreground
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

    def _key_handler(self, k):
        # Return the action (a function) to do according the pressed key (k).
        if k == xkeysyms.keysyms['Tab']:
            return self._trigger_complete
        self.actual_value = self.completer.actual()
        self.completer.reset()
        if k < 127 and chr(k) in string.printable:
            self.key = k
            return self._write_char
        if k == xkeysyms.keysyms['BackSpace']:
            return self._backspace
        if k == xkeysyms.keysyms['Escape']:
            return self._unfocus
        if k in (xkeysyms.keysyms['Return'],
                 xkeysyms.keysyms['KP_Enter']):
            return self._send_cmd
        if k in (xkeysyms.keysyms['Up'],
                 xkeysyms.keysyms['KP_Up']):
            return self._get_prev_cmd
        if k in (xkeysyms.keysyms['Down'],
                 xkeysyms.keysyms['KP_Down']):
            return self._get_next_cmd

    def handle_KeyPress(self, e):
        """KeyPress handler for the minibuffer.

        Currently only supports ASCII characters.
        """
        state = e.state & ~(self.qtile.numlockMask)
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, state)
        handle_key = self._key_handler(keysym)
        if handle_key:
            handle_key()
        self._update()

    def cmd_fake_keypress(self, key):
        class Dummy:
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
