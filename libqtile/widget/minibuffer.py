from .. import hook, bar, manager, xcbq
import base
import xcb
from .. import xkeysyms

class Minibuffer(base._TextBox):

    defaults = manager.Defaults(
        ("font", "Monospace", "Font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, " ", width, **config)
        self.name = "minibuffer"

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

    def startInput(self, message, callback):
        """
            Displays a message and starts to take one line of
            keyboard input from the user.
            When done, calls the callback with the input string
            as argument.
        """
        self.message = message
        self.userInput = ""
        self.callback = callback
        self.text = "%s: %s" % (self.message, self.userInput)
        self.guess_width()
        self.bar.draw()
        self.bar.widget_grab_keyboard(self)

    def handle_KeyPress(self, e):
        """
            KeyPress handler for the minibuffer.
            Currently only supports ASCII characters.
        """
        keysym = self.qtile.conn.keycode_to_keysym(e.detail, e.state)
        if keysym < 127:
            # No LookupString in XCB... oh, the shame! Unicode users beware!
            self.userInput += chr(keysym)
            self.text = "%s: %s" % (self.message, self.userInput)
        elif keysym == xkeysyms.keysyms['BackSpace'] and len(self.userInput) > 0:
            self.userInput = self.userInput[:-1]
            self.text = "%s: %s" % (self.message, self.userInput)
        elif keysym == xkeysyms.keysyms['Escape']:
            self.text = ""
            self.bar.widget_ungrab_keyboard()
        elif keysym == xkeysyms.keysyms['Return']:
            self.text = ""
            self.bar.widget_ungrab_keyboard()
            self.callback(self.userInput)
        self.guess_width()
        self.bar.draw()

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return dict(
            name = self.name,
            width = self.width,
        )

