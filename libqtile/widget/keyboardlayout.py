"""
   Widgets for changing and displaying the current keyboard layout
   with text or with icon.
   In the case of icon, if the mouse is over the widget, the text version 
   is printed in a popup window.
   It requires setxkbmap to be available in the sytem.
"""

import subprocess
from subprocess import CalledProcessError
import base
from libqtile import bar, hook
import os
import cairo

# for the popup window
from libqtile import notify_window
from textbox import TextBox


def default_icon_path():
    """
        Define the icon path
        files are of the layout/flag.png pattern (eg. us/flag.png)
    """
    return "/usr/share/locale/l10n/"


class _KeyboardLayout(base._TextBox):
    """
        Widget for changing and displaying the current keyboard layout.
        It requires setxkbmap to be available in the sytem.
    """
    defaults = [
        ("update_interval", 1, "Update time in seconds."),
    ]


    def __init__(self, configured_keyboards=['us'],
                 width=bar.CALCULATED, with_variant=False, **config):
        """
            :configured_keyboards A list of predefined keyboard layouts
            represented as strings. For example: ['us', 'us colemak', 'es', 'fr'].
        """
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(_KeyboardLayout.defaults)
        self.configured_keyboards = configured_keyboards
        self.with_variant = with_variant

    def _other_keyboard(self, direction):
        """
            Set the previous or next layout in the list of configured keyboard
            layouts as then new current layout in use.
            If the current keyboard layout is not in the list, it will set as
            new layout the first one in the list.
        """
        current_keyboard = self._get_keyboard().layout
        if current_keyboard in self.configured_keyboards:
            # iterate the list circularly
            next_keyboard = self.configured_keyboards[
                (self.configured_keyboards.index(current_keyboard) + direction) %
                len(self.configured_keyboards)]
        else:
            next_keyboard = self.configured_keyboards[0]
        self._set_keyboard(next_keyboard)


    def next_keyboard(self):
        """
            Set the next layout in the list of configured keyboard layouts as
            new current layout in use.
            If the current keyboard layout is not in the list, it will set as
            new layout the first one in the list.
        """
        self._other_keyboard(1)


    def previous_keyboard(self):
        """
            Set the previous layout in the list of configured keyboard layouts as
            new current layout in use.
            If the current keyboard layout is not in the list, it will set as
            new layout the first one in the list.
        """
        self._other_keyboard(-1)


    def _get_keyboard(self):
        """
            Return the currently used keyboard layout as a string.
            Examples: "us", "us dvorak".
            In case of error returns "unknown".
        """
        try:
            setxkbmap_out = subprocess.check_output(['setxkbmap', '-query'])
            keyboard = _Keyboard().from_setxkbmap_query(setxkbmap_out)
            return keyboard
        except CalledProcessError as e:
            self.log.error('Can not change the keyboard layout: {0}'
                           .format(e))
        except OSError as e:
            self.log.error('Please, check that setxkbmap is available: {0}'
                           .format(e))
        return "unknown"


    def _set_keyboard(self, keyboard):
        command = ['setxkbmap']
        command.extend(keyboard.split(" "))
        try:
            subprocess.check_call(command)
        except CalledProcessError as e:
            self.log.error('Can not change the keyboard layout: {0}'
                           .format(e))
        except OSError as e:
            self.log.error('Please, check that setxkbmap is available: {0}'
                           .format(e))


    def _get_text(self):
        kb = self._get_keyboard()
        if not self.with_variant:
            text = kb.layout
        else:
            text = str(kb)
        return text
    

class KeyboardLayout(_KeyboardLayout):
    """
        Widget for changing and displaying the current keyboard layout
        Text mode
    """

    def __init__(self, configured_keyboards=['us'],  **config):
        _KeyboardLayout.__init__(self, configured_keyboards, **config)
        """

        """
        self.text = self._get_text()

        self.setup_hook()


    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self._get_text()


    def button_press(self, x, y, button):
        """
            If leftmost button of the mouse is clicked, switch to next layout
        """
        if button == 1:
            self.next_keyboard()
        elif button == 3:
            self.previous_keyboard()
        if button in [1, 3]:
            hook.fire("keyboard_layout_change", None)
        


    def setup_hook(self):
        def hook_response(_):
            
            self.text = self._get_text()
            self.bar.draw()
        hook.subscribe.keyboard_layout_change(hook_response)




class KeyboardLayoutIcon(_KeyboardLayout):
    """
        Widget for changing and displaying the current keyboard layout
        Icon mode
    """
    
    defaults = [
        ('theme_path', default_icon_path(), 'Path of the icons'),
        ('custom_icons', {}, 'dict containing key->filename icon map'),
    ]

    def __init__(self, configured_keyboards=['us'], **config):
        _KeyboardLayout.__init__(self, configured_keyboards, **config)
        self.add_defaults(KeyboardLayoutIcon.defaults)

        if self.theme_path:
            self.width_type = bar.STATIC
            self.width = 0
        self.surfaces = {}

        #fill the icons dictionary with current defined layouts
        self.current_icon = 'us'
        self.icons = {'us':'us/flag.png'}
        for k in self.configured_keyboards:
            self.icons[k] = os.sep.join([k, 'flag.png'])

        self.icons.update(self.custom_icons)
        self.setup_hook()
        self.popup = None


    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.setup_images()
        icon = self._get_keyboard().layout
        if icon != self.current_icon:
            self.current_icon = icon
            self.draw()


    def setup_hook(self):
        def icon_hook_response(_):
            icon = self._get_keyboard().layout
            if icon != self.current_icon:
                self.current_icon = icon
                self.draw()
        hook.subscribe.keyboard_layout_change(icon_hook_response)


    def button_press(self, x, y, button):
        if button == 1:
            self.next_keyboard()
        elif button == 3:
            self.previous_keyboard()
        if button in [1, 3]:
            hook.fire("keyboard_layout_change", None)
            if self.popup:
                self.popup.widgets[0].text = str(self._get_keyboard())
                self.popup.draw()

    def pointer_over(self, x, y, detail):
        if not self.popup:
            # clean if there are some popups form other widget alive
            for w in self.bar.popup_window.keys():
                w.leave_window(x, y, detail)

            self.popup = notify_window.NotifyWindow(self, [TextBox(str(self._get_keyboard()), fontsize=self.fontsize)])
            self.bar.popup_window[self] = self.popup
            self.popup._configure(self.qtile, self.bar.screen)


    def leave_window(self, x, y, detail):
        if self.popup:
            self.popup.window.hide()
            self.popup.window.kill()
            self.popup.window = None
            self.popup = None
            self.bar.popup_window.pop(self)


    def setup_images(self):
        for key, name in self.icons.iteritems():
            if key in self.surfaces.keys():
                continue
            try:
                path = os.path.join(self.theme_path, name)
                img = cairo.ImageSurface.create_from_png(path)
            except cairo.Error:
                self.theme_path = None
                self.qtile.log.warning('Current Layout Icon switching to text mode')
                return
            input_width = img.get_width()
            input_height = img.get_height()

            sp = input_height / float(self.bar.height - 10)

            width = input_width / sp
            if width > self.width:
                self.width = int(width) + self.actual_padding * 2
                
            imgpat = cairo.SurfacePattern(img)

            scaler = cairo.Matrix()

            scaler.scale(sp, sp)
            scaler.translate(self.actual_padding * -1, -5)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairo.FILTER_BEST)
            self.surfaces[key] = imgpat


    def draw(self):
        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            self.drawer.ctx.set_source(self.surfaces[self.current_icon])
            self.drawer.ctx.paint()
            self.drawer.draw(self.offset, self.width)
        else:
            self.text = self.current_icon
            base._TextBox.draw(self)





class _Keyboard(object):
    """
        Canonical representation of a keyboard layout. It provides some utility
        methods to build/transform it from/to some other representations.
    """
    def __init__(self):
        self.with_variant = False

    def __str__(self):
        if not self.variant:
            return self.layout
        else:
            return self.layout + " " + self.variant

    def from_dict(self, dictionary):
        """
            Accept a dict containing as keys the layout and variant of a
            keyboard layout.
        """
        self.layout = dictionary.get('layout')
        kbs = self.layout.split(",")
        if len(kbs) > 1:
            self.layout = kbs[0]
        self.variant = dictionary.get('variant')
        return self

    def from_setxkbmap_query(self, setxkbmap_out):
        """
            Accept a setxkbmap query represented as a string.
        """
        return self.from_dict(
            dict((a, b.strip()) for a, b in
                 (item.split(":") for item in
                  setxkbmap_out.splitlines()))
            )
