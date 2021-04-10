# Copyright (c) 2021 Matt Colligan
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

from pywayland.server import Listener
from wlroots import ffi, lib
from wlroots.wlr_types.keyboard import KeyboardModifier, KeyState
from xkbcommon import xkb

from libqtile.log_utils import logger


def _get_keysyms(xkb_state, keycode):
    syms_out = ffi.new("const xkb_keysym_t **")
    nsyms = lib.xkb_state_key_get_syms(xkb_state, keycode, syms_out)
    if nsyms > 0:
        assert syms_out[0] != ffi.NULL

    syms = [syms_out[0][i] for i in range(nsyms)]
    logger.debug(f"Got {nsyms} syms: {syms}")
    return syms


class Keyboard:
    def __init__(self, core, device):
        self.core = core
        self.device = device
        self.seat = core.seat
        self.keyboard = device.keyboard

        xkb_context = xkb.Context()
        self.keyboard.set_keymap(xkb_context.keymap_new_from_names())
        self.keyboard.set_repeat_info(25, 600)

        self._on_modifier_listener = Listener(self._on_modifier)
        self._on_key_listener = Listener(self._on_key)
        self._on_destroy_listener = Listener(self._on_destroy)
        self.keyboard.modifiers_event.add(self._on_modifier_listener)
        self.keyboard.key_event.add(self._on_key_listener)
        self.keyboard.destroy_event.add(self._on_destroy_listener)

    def finalize(self):
        self._on_modifier_listener.remove()
        self._on_key_listener.remove()
        self._on_destroy_listener.remove()
        self.core.keyboards.remove(self)
        if self.core.keyboards and self.core.seat.keyboard._ptr == self.keyboard._ptr:
            self.seat.set_keyboard(self.core.keyboards[-1].device)

    def _on_destroy(self, _listener, data):
        logger.debug("Signal: keyboard destroy")
        self.finalize()

    def _on_modifier(self, _listener, event):
        logger.debug("Signal: keyboard modifier")
        self.seat.keyboard_notify_modifiers(self.keyboard.modifiers)

    def _on_key(self, _listener, event):
        logger.debug("Signal: keyboard key")
        # TODO: handle key combinations for calling key bindings
        if event.state == KeyState.KEY_PRESSED:
            if self.keyboard.modifier == KeyboardModifier.ALT:
                # translate libinput keycode -> xkbcommon
                keycode = event.keycode + 8
                for keysym in _get_keysyms(self.keyboard._ptr.xkb_state, keycode):
                    if keysym == xkb.keysym_from_name("Escape"):
                        self.core.display.terminate()
                        return

        self.seat.keyboard_notify_key(event)
