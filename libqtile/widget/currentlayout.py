""" 
Widget that display the current layout used
- by text with CurrentLayout
- by icons with CurrentLayoutIcon

Default icons path is ../resources/layout-icons/

Defaults icon file names:  layoutname.png
eg:  'floating' layout -> floating.png
other known layout names:
- 'max',
- 'matrix',
- 'ratiotile',
- 'slice',
- 'stack',
- 'tile', 
- 'treetab',
- 'monadtall',
- 'zoomy',

"""

import cairo
import base
from libqtile import bar, hook
import os

# for the popup window
from libqtile import notify_window
from textbox import TextBox 


def default_icon_path():
    """ Define the icon path relativement to the this file """
    root = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
    return os.path.join(root, 'resources', 'layout-icons')



class _CurrentLayout(base._TextBox):
    """ Base current layout class """
    def __init__(self, width=bar.CALCULATED, **config ):
        base._TextBox.__init__(self, "", width, **config)


class CurrentLayout(_CurrentLayout):
    """ Class printing the name of the current layout """
    
    def __init__(self, **config):
        _CurrentLayout.__init__(self, **config)
        
    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self.bar.screen.group.layouts[0].name
        self.setup_hooks()

    def setup_hooks(self):
        """ define a hook function in case of layout changing """
        def hook_response(layout, group):
            if group.screen is not None and group.screen == self.bar.screen:
                self.text = layout.name
                self.bar.draw()
        hook.subscribe.layout_change(hook_response)

    def button_press(self, x, y, button):
        """ Two actions are defined in case of button press on the widget """
        if button == 1:
            # leftmost button
            self.qtile.cmd_nextlayout()
        elif button == 3:
            # rightmost button
            self.qtile.cmd_prevlayout()



class CurrentLayoutIcon(_CurrentLayout):
    """
    Draw the icon of the current layout

    """

    defaults = [
        ('theme_path', default_icon_path(), 'Path of the icons'),
        ('custom_icons', {}, 'dict containing key->filename icon map'),
    ]


    def __init__(self, **config ):
        _CurrentLayout.__init__(self, **config)
        self.add_defaults(CurrentLayoutIcon.defaults)
        
        if self.theme_path:
            self.width_type = bar.STATIC
            self.width = 0
        self.surfaces = {}
        # initialisation with a default value
        self.current_icon = 'floating'
        self.icons = {'floating':'floating.png'}
        self.icons.update(self.custom_icons)
        self.popup = None


    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

        #fill the icons dictionary with current defined layouts
        for la in bar.screen.group.layouts:
            self.icons[la.name] = '{0}.png'.format(la.name)
        self.setup_images()


        icon = self.bar.screen.group.layouts[0].name
        if icon != self.current_icon:
            self.current_icon = icon
            self.draw()
        self.setup_hooks()


    def pointer_over(self, x, y, detail):
        if not self.popup:
            # clean if there are some popups form other widget alive
            for w in self.bar.popup_window.keys():
                w.leave_window(x, y, detail)

            self.popup = notify_window.NotifyWindow(self, [TextBox(self.bar.screen.group.layout.name, fontsize=self.fontsize)])
            self.bar.popup_window[self] = self.popup
            self.popup._configure(self.qtile, self.bar.screen)


    def leave_window(self, x, y, detail):
        if self.popup:
            self.popup.window.hide()
            self.popup.window.kill()
            self.popup.window = None
            self.popup = None
            self.bar.popup_window.pop(self)


    def draw(self):
        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            self.drawer.ctx.set_source(self.surfaces[self.current_icon])
            self.drawer.ctx.paint()
            self.drawer.draw(self.offset, self.width)
        else:
            self.text = self.current_icon
            base._TextBox.draw(self)


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

            sp = input_height / float(self.bar.height - 1)

            width = input_width / sp
            if width > self.width:
                self.width = int(width) + self.actual_padding * 2

            imgpat = cairo.SurfacePattern(img)

            scaler = cairo.Matrix()

            scaler.scale(sp, sp)
            scaler.translate(self.actual_padding * -1, 0)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairo.FILTER_BEST)
            self.surfaces[key] = imgpat


    def setup_hooks(self):
        def hook_response(layout, group):
            if group.screen is not None and group.screen == self.bar.screen:
                icon = layout.name
                if icon != self.current_icon:
                    # in case of the layout was not in the initial config.py
                    if icon not in self.icons:
                        self.icons[icon] = '{0}.png'.format(icon)
                        self.setup_images()
                    self.current_icon = icon
                    self.draw()
                    # for the popup window
                    if self.popup:
                        self.popup.widgets[0].text = self.bar.screen.group.layout.name
                        self.popup.draw()
        hook.subscribe.layout_change(hook_response)


    def button_press(self, x, y, button):
        if button == 1:
            self.qtile.cmd_nextlayout()
        elif button == 3:
            self.qtile.cmd_prevlayout()


