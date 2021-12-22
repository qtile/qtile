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

from __future__ import annotations

import typing

from pywayland.protocol.wayland import WlKeyboard
from wlroots import ffi, lib
from xkbcommon import xkb

from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Dict, Optional, Tuple

    from wlroots.wlr_types import InputDevice
    from wlroots.wlr_types.keyboard import KeyboardKeyEvent

    from libqtile.backend.wayland.core import Core

KEY_PRESSED = WlKeyboard.key_state.pressed
KEY_RELEASED = WlKeyboard.key_state.released

# Keep this around instead of creating it on every key
xkb_keysym = ffi.new("const xkb_keysym_t **")


class Keyboard(HasListeners):
    def __init__(self, core: Core, device: InputDevice):
        self.core = core
        self.device = device
        self.qtile = core.qtile
        self.seat = core.seat
        self.keyboard = device.keyboard
        self.grabbed_keys = core.grabbed_keys

        self.keyboard.set_repeat_info(25, 600)
        self.xkb_context = xkb.Context()
        self._keymaps: Dict[Tuple[Optional[str], ...], xkb.Keymap] = {}
        self.set_keymap(None, None, None)

        self.add_listener(self.keyboard.modifiers_event, self._on_modifier)
        self.add_listener(self.keyboard.key_event, self._on_key)
        self.add_listener(self.keyboard.destroy_event, self._on_destroy)

    def finalize(self):
        self.finalize_listeners()
        self.core.keyboards.remove(self)
        if self.core.keyboards and self.core.seat.keyboard.destroyed:
            self.seat.set_keyboard(self.core.keyboards[-1].device)

    def set_keymap(
        self, layout: Optional[str], options: Optional[str], variant: Optional[str]
    ) -> None:
        """
        Set the keymap for this keyboard.
        """
        if (layout, options, variant) in self._keymaps:
            keymap = self._keymaps[(layout, options, variant)]
        else:
            keymap = self.xkb_context.keymap_new_from_names(
                layout=layout, options=options, variant=variant
            )
            self._keymaps[(layout, options)] = keymap
        self.keyboard.set_keymap(keymap)

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: keyboard destroy")
        self.finalize()

    def _on_modifier(self, _listener, _data):
        self.seat.set_keyboard(self.device)
        self.seat.keyboard_notify_modifiers(self.keyboard.modifiers)

    def _on_key(self, _listener, event: KeyboardKeyEvent):
        if self.qtile is None:
            # shushes mypy
            self.qtile = self.core.qtile
            assert self.qtile is not None

        if event.state == KEY_PRESSED:
            # translate libinput keycode -> xkbcommon
            keycode = event.keycode + 8
            layout_index = lib.xkb_state_key_get_layout(self.keyboard._ptr.xkb_state, keycode)
            nsyms = lib.xkb_keymap_key_get_syms_by_level(
                self.keyboard._ptr.keymap,
                keycode,
                layout_index,
                0,
                xkb_keysym,
            )
            keysyms = [xkb_keysym[0][i] for i in range(nsyms)]
            mods = self.keyboard.modifier
            for keysym in keysyms:
                if (keysym, mods) in self.grabbed_keys:
                    self.qtile.process_key_event(keysym, mods)
                    return

            if self.core.focused_internal:
                self.core.focused_internal.process_key_press(keysym)
                return

        self.seat.keyboard_notify_key(event)
