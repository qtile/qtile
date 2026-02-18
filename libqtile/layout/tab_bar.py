from libqtile.backend.base.drawer import TextLayout
from libqtile.backend.base import Internal, Drawer

# these types are needed even if not type checking, I need them for a typeddict
from typing import TYPE_CHECKING, TypedDict, Optional, List, Dict, Callable
from libqtile.core.manager import Qtile
from libqtile.config import ScreenRect


class TabBarConfig(TypedDict):
    bar_color: str
    tab_padding: int
    unfocused_tab_bg: str
    focused_tab_bg: str
    unfocused_tab_text_color: str
    focused_tab_text_color: str
    tab_font: str
    tab_fontsize: int
    # each callback determines what the nth tab does when clicked
    mouse_callbacks: Optional[
        Dict[int, Callable[[int], None]]
    ]  # mouse button id -> callback


class TabBar:
    # A generic horizontal qtile tab bar with clickable tabs
    # intended to switch between windows in layouts like "max" or "columns"
    # but could be used for other purposes as well
    def __init__(
        self,
        qtile: Qtile,
        initial_placement: ScreenRect,
        initial_tabs: List[str],
        config: TabBarConfig,
        initial_focused_index=0,
    ) -> None:

        # static options
        self.bar_color = config["bar_color"]
        self.unfocused_tab_text_color = config["unfocused_tab_text_color"]
        self.focused_tab_text_color = config["focused_tab_text_color"]
        self.unfocused_tab_bg = config["unfocused_tab_bg"]
        self.focused_tab_bg = config["focused_tab_bg"]
        self.tab_padding = config["tab_padding"]
        self.tab_font = config["tab_font"]
        self.tab_fontsize = config["tab_fontsize"]
        self.mouse_callbacks = config.get("mouse_callbacks", {})

        # variables
        self.rect = initial_placement
        self.tabs = initial_tabs
        self.focused_index = initial_focused_index
        self.bar: Internal = qtile.core.create_internal(
            self.rect.x, self.rect.y, self.rect.width, self.rect.height
        )
        self.bar.process_window_expose = self.draw
        self.bar.process_button_click = self.handle_click

    @property
    def tab_width(self) -> int:
        return self.rect.width // len(self.tabs)

    def _create_drawer(self, screen_rect: ScreenRect) -> None:
        if hasattr(self, "drawer") and self.drawer is not None:
            if (
                self.drawer.width != self.rect.width
                or self.drawer.height != self.rect.height
            ):
                self.drawer.finalize()
                self.drawer = None

        if not hasattr(self, "drawer") or self.drawer is None:
            self.drawer: Drawer = self.bar.create_drawer(
                self.rect.width, self.rect.height
            )

    def draw(self):
        if not self.drawer:
            return

        self.drawer.clear(self.bar_color)
        offset = 0
        for idx, tab_text in enumerate(self.tabs):
            if idx == self.focused_index:
                bg_color = self.focused_tab_bg
                text_color = self.focused_tab_text_color
            else:
                bg_color = self.unfocused_tab_bg
                text_color = self.unfocused_tab_text_color

            self.drawer.set_source_rgb(bg_color)
            self.drawer.fillrect(
                offset, 0, self.tab_width - self.tab_padding, self.rect.height
            )

            text_layout = TextLayout(
                self.drawer,
                tab_text,
                text_color,
                self.tab_font,
                self.tab_fontsize,
                None,
                wrap=False,
            )
            text_layout.width = self.tab_width
            text_layout.draw(
                offset
                + (self.tab_width - text_layout.width) // 2,  # Center horizontally
                (self.rect.height - text_layout.height) // 2,  # Center vertically
            )
            offset += self.tab_width
        self.drawer.draw()

    def handle_click(self, x, y, button):
        tab_idx = int(x // self.tab_width)
        if 0 <= tab_idx < len(self.tabs):
            if button in self.mouse_callbacks:
                self.mouse_callbacks[button](tab_idx)

    # these methods will need to be called in the corresponding methods in the imporing layout
    # screen_rect should always be the actual area that the bar occupies on the screen
    def configure(
        self,
        screen_rect: ScreenRect | None = None,
        focused_index: int | None = None,
        tabs: list[str] | None = None,
    ):
        if screen_rect is not None:
            self.rect = screen_rect
            self._create_drawer(screen_rect)

        if focused_index is not None:
            self.focused_index = focused_index

        if tabs is not None:
            self.tabs = tabs

        self.bar.place(
            self.rect.x, self.rect.y, self.rect.width, self.rect.height, 0, None
        )
        self._create_drawer(self.rect)
        self.draw()
        self.bar.unhide()

    def hide(self):
        """
        Hides the tab bar
        Callout when hiding the layout
        Also good for when you just want to hide the tab bar
        """
        self.bar.hide()

    def show(self, screen_rect: ScreenRect | None = None):
        """
        to be called when layout is shown. Not necessarily to show the tab bar
        to show the bar in other situations, call configure
        """
        if screen_rect is not None:
            self.rect = screen_rect
        self.bar.unhide()
        self.draw()

    def finalize(self):
        """Clean up resources"""
        if hasattr(self, "drawer") and self.drawer is not None:
            self.drawer.finalize()
        if self.bar:
            self.bar.kill()
