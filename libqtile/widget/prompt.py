import time, sys, os, bisect, glob
from .. import hook, bar, manager, xkeysyms, xcbq
import base


class NullCompleter:
    def actual(self):
        return txt

    def complete(self, txt):
        return txt


class CommandCompleter:
    DEFAULTPATH = "/bin:/usr/bin:/usr/local/bin"
    def __init__(self, _testing=False):
        """
            _testing: disables reloading of the lookup table to make testing possible.
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
                if txt[0] in "~/":
                    path = os.path.expanduser(txt)
                    if os.path.isdir(path):
                        files = glob.glob(os.path.join(path, "*"))
                        prefix = txt
                    else:
                        files = glob.glob(path+"*")
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
                            for cmd in glob.glob(os.path.join(d, "%s*"%txt)):
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
        "cmd": CommandCompleter,
        None: NullCompleter
    }
    defaults = manager.Defaults(
        ("font", "Monospace", "Font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour"),
        ("cursorblink", 0.5, "Cursor blink rate. 0 to disable.")
    )
    def __init__(self, name="prompt", **config):
        base._TextBox.__init__(self, " ", bar.CALCULATED, **config)
        self.name = name
        self.active = False
        self.blink = False
        self.lasttick = 0
        self.completer = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        if self.cursorblink:
            hook.subscribe.tick(self.tick)

    def startInput(self, prompt, callback, complete=None):
        """
            complete: Tab-completion. Can be None, or "cmd".

            Displays a prompt and starts to take one line of keyboard input
            from the user. When done, calls the callback with the input string
            as argument.
        """
        self.active = True
        self.prompt = prompt
        self.userInput = ""
        self.callback = callback
        self.completer = self.completers[complete]()
        self._update()
        self.bar.widget_grab_keyboard(self)

    def tick(self):
        t = time.time()
        if self.lasttick + self.cursorblink < t:
            self.lasttick = t
            self.blink = not self.blink
            self._update()

    def _update(self):
        if self.active:
            self.text = "%s%s"%(self.prompt, self.userInput)
            if self.blink:
                self.text = self.text + "_"
            else:
                self.text = self.text + " "
        else:
            self.text = ""
        self.bar.draw()

    def handle_KeyPress(self, e):
        """
            KeyPress handler for the minibuffer.
            Currently only supports ASCII characters.
        """
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, e.state)
        if keysym == xkeysyms.keysyms['Tab']:
            self.userInput = self.completer.complete(self.userInput)
        else:
            self.completer.reset()
            if keysym < 127:
                # No LookupString in XCB... oh, the shame! Unicode users beware!
                self.userInput += chr(keysym)
            elif keysym == xkeysyms.keysyms['BackSpace'] and len(self.userInput) > 0:
                self.userInput = self.userInput[:-1]
            elif keysym == xkeysyms.keysyms['Escape']:
                self.active = False
                self.bar.widget_ungrab_keyboard()
            elif keysym == xkeysyms.keysyms['Return']:
                self.active = False
                self.bar.widget_ungrab_keyboard()
                self.callback(self.userInput)
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
            name = self.name,
            width = self.width,
        )

