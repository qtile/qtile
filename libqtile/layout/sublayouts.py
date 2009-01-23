from base import SubLayout, Rect

class VerticalStack(SubLayout):
    def layout(self, rectangle, windows):
        def color(color):
                colormap = self.clientStack.group.qtile.display.screen().default_colormap
                return colormap.alloc_named_color(color).pixel
        self.active_border = color(self.theme["verticalstack_border_active"])
        self.focused_border = color(self.theme["verticalstack_border_active"])
        self.normal_border = color(self.theme["verticalstack_border_normal"])
        self.border_width = self.theme["verticalstack_border_width"]
        SubLayout.layout(self, rectangle, windows)

    def configure(self, r, client):
        position = self.windows.index(client)
        cliheight = int(r.h / len(self.windows)) #inc border
        client.place(r.x + self.border_width,
                     r.y + cliheight * position + self.border_width,
                     r.w - 2*self.border_width,
                     cliheight - 2*self.border_width,
                     self.border_width,
                     self.normal_border, #TODO: make this change for focus
                     )
        client.unhide()
                     
