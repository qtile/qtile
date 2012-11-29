import glob
import os
import string
from .. import bar, manager, xkeysyms, xcbq, command
import base


class NullCompleter:
    def __init__(self, qtile):
        self.qtile = qtile
        self.thisfinal = ""

    def actual(self, qtile):
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
            for wid, window in self.qtile.windowMap.iteritems():
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
        self.lookup, self.offset = None, None
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
    defaults = manager.Defaults(
        ("font", "Arial", "Font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None,
            "font shadow color, default is None(no shadow)"),
        ("padding", None, "Padding. Calculated if None."),
        ("background", None, "Background colour"),
        ("foreground", "ffffff", "Foreground colour"),
        ("cursorblink", 0.5, "Cursor blink rate. 0 to disable.")
    )

    def __init__(self, name="prompt", **config):
        base._TextBox.__init__(self, "", bar.CALCULATED, **config)
        self.name = name
        self.active = False
        self.blink = False
        self.completer = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

    def startInput(self, prompt, callback, complete=None):
        """
            complete: Tab-completion. Can be None, or "cmd".

            Displays a prompt and starts to take one line of keyboard input
            from the user. When done, calls the callback with the input string
            as argument.
        """

        if self.cursorblink and not self.active:
            self.timeout_add(self.cursorblink, self._blink)

        self.active = True
        self.prompt = prompt
        self.userInput = ""
        self.callback = callback
        self.completer = self.completers[complete](self.qtile)
        self._update()
        self.bar.widget_grab_keyboard(self)

    def _calculate_real_width(self):
        if self.blink:
            return min(self.layout.width,
                self.bar.width) + self.actual_padding * 2
        else:
            _text = self.text
            self.text = _text + "_"
            width = min(self.layout.width,
                self.bar.width) + self.actual_padding * 2
            self.text = _text
            return width

    def calculate_width(self):
        if self.text:
            return self._calculate_real_width()
        else:
            return 0

    def _blink(self):
        self.blink = not self.blink
        self._update()
        if not self.active:
            return False
        return True

    def _update(self):
        if self.active:
            self.text = "%s%s" % (self.prompt, self.userInput)
            if self.blink:
                self.text = self.text + "_"
            else:
                self.text = self.text
        else:
            self.text = ""
        self.bar.draw()

    def handle_KeyPress(self, e):
        """
            KeyPress handler for the minibuffer.
            Currently only supports ASCII characters.
        """
        state = e.state & ~(self.qtile.numlockMask)
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, state)
        if keysym == xkeysyms.keysyms['Tab']:
            self.userInput = self.completer.complete(self.userInput)
        else:
            actual_value = self.completer.actual()
            self.completer.reset()
            if keysym < 127 and chr(keysym) in string.printable:
                # No LookupString in XCB... oh,
                # the shame! Unicode users beware!
                self.userInput += chr(keysym)
            elif (keysym == xkeysyms.keysyms['BackSpace'] and
                  len(self.userInput) > 0):
                self.userInput = self.userInput[:-1]
            elif keysym == xkeysyms.keysyms['Escape']:
                self.active = False
                self.bar.widget_ungrab_keyboard()
            elif keysym == xkeysyms.keysyms['Return']:
                self.active = False
                self.bar.widget_ungrab_keyboard()
                self.callback(actual_value or self.userInput)
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
