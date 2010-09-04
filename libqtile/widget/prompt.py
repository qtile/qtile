import time, sys, os, bisect, glob
from .. import hook, bar, manager, xkeysyms
import base


class NullCompleter:
    def final(self):
        return txt

    def complete(self, txt):
        return txt


class CommandCompleter:
    DEFAULTPATH = "/bin:/usr/bin:/usr/local/bin"
    def __init__(self, _testing=False):
        """
            _testing: disables reloading of the lookup table to make testing possible.
        """
        self.lookup, self.last, self.offset = None, None, None
        self.thisfinal = None
        self._testing = _testing

    def final(self):
        return self.thisfinal

    def complete(self, txt):
        """
            Returns the next completion for txt, or None if there is no completion.
        """
        if not txt == self.last:
            if not self._testing:
                dirs = os.environ.get("PATH", self.DEFAULTPATH).split(":")
                self.lookup = []
                for didx, d in enumerate(dirs):
                    try:
                        for cmd in glob.glob(os.path.join(d, "%s*"%txt)):
                            self.lookup.append((os.path.basename(cmd), d))
                    except OSError:
                        pass

            self.lookup.sort()
            self.last = txt
            self.offset = 0
        else:
            self.offset += 1
        start = bisect.bisect_left(self.lookup, (txt, 0))
        if start >= len(self.lookup):
            self.thisfinal = txt
            return txt
        if start + self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[min(start + self.offset, len(self.lookup))]
        if not ret[0].startswith(txt):
            if self.offset:
                self.offset = 0
                ret = self.lookup[start + self.offset]
            else:
                self.thisfinal = txt
                return txt
        self.thisfinal = os.path.join(ret[1], ret[0])
        return ret[0]


class Prompt(base._TextBox):
    """
        A widget that prompts for user input. Input should be started using the
        .startInput method on this class.
    """
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

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        if self.cursorblink:
            hook.subscribe.tick(self.tick)

    def startInput(self, prompt, callback):
        """
            Displays a prompt and starts to take one line of
            keyboard input from the user.
            When done, calls the callback with the input string
            as argument.
        """
        self.active = True
        self.prompt = prompt
        self.userInput = ""
        self.callback = callback
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
        self.guess_width()
        self.bar.draw()

    def handle_KeyPress(self, e):
        """
            KeyPress handler for the minibuffer.
            Currently only supports ASCII characters.
        """
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, e.state)
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

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return dict(
            name = self.name,
            width = self.width,
        )

