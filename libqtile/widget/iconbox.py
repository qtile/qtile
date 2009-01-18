import base

import Image #PYTHON IMAGING LIBRARY - new dependency

class IconBox(base._Widget):
    def __init__(self, name, icon, resize=True):
        self.name = name
        if type(icon) is str:
            self.icon = Image.open(icon)
        else:
            self.icon = icon #should be a pil image
        self.resize = resize

    def _configure(self, qtile, bar, event):
        base._Widget._configure(self, qtile, bar, event)
        if not self.resize:
            self.width = self.icon.size[0]
        else:
            iconsize = self.icon.size
            scale = float(self.bar.size)/iconsize[1]
            new_size = tuple([int(scale * d) for d in iconsize])
            self.icon.thumbnail(new_size, Image.ANTIALIAS)
            self.width = self.icon.size[0]
        self.icon = self.icon.convert('RGB') #convert here instead, after resize
    def draw(self):
        self.clear()
        self._drawer.win.put_pil_image(self._drawer.gc,
                                       self.offset,
                                       0,
                                       self.icon
                                       )
