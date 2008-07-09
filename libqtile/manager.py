import Xlib
import Xlib.protocol.event as event
import Xlib.X as X
import ipc


class Screen:
    def __init__(self, width, height):
        self.width, self.height = width, height


class Group:
    pass


class Client:
    pass


class QTile:
    def __init__(self, display, fname):
        self.display = Xlib.display.Display(display)
        self.fname = fname
        scrn = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = scrn.root
        self.screens = [
            Screen(
                scrn.width_in_pixels,
                scrn.height_in_pixels
            )
        ]
        self.root.change_attributes(
            event_mask = X.SubstructureNotifyMask
        )
        self.display.set_error_handler(self.errorHandler)
        self.server = ipc.Server(self.fname, self.command)

    def loop(self):
        while 1:
            self.server.receive()

    def errorHandler(self, *args, **kwargs):
        print args, kwargs

    def command(self, data):
        command, args = data
        parts = command.split(".")
        print parts
        return "OK"

    def cmd_status(self):
        return "OK"
        pass


