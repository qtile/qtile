from __future__ import annotations

import functools
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from pywayland.utils import wl_container_of, wl_list_for_each
from wlroots import ffi, lib
from wlroots.wlr_types.scene import SceneNode, SceneNodeType, SceneRect

from libqtile import utils

if TYPE_CHECKING:
    from wlroots.wlr_types.scene import SceneTree

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.output import Output
    from libqtile.backend.wayland.window import WindowType
    from libqtile.utils import ColorType


@functools.lru_cache()
def _rgb(color: ColorType) -> ffi.CData:
    """Helper to create and cache float[4] arrays for border painting"""
    if isinstance(color, ffi.CData):
        return color
    return ffi.new("float[4]", utils.rgb(color))


class Renderer(metaclass=ABCMeta):
    """This class is responsible for rendering the scene graph.

    This includes painting borders.
    """

    def __init__(self, core: Core) -> None:
        self.core = core

    def finalize(self) -> None:
        pass

    @abstractmethod
    def create_borders(
        self, window: WindowType, tree: SceneTree, colors: list[ColorType], width: int
    ) -> None:
        pass

    @abstractmethod
    def destroy_borders(self, window: WindowType, tree: SceneTree) -> None:
        pass

    @abstractmethod
    def render(self, output: Output) -> None:
        pass


class WlrootsRenderer(Renderer):
    """This renderer uses the wlroots scene graph renderer."""

    def create_borders(
        self, window: WindowType, tree: SceneTree, colors: list[ColorType], width: int
    ) -> None:
        # The borders are wlr_scene_rects.
        # They come in groups of four: N, E, S, W edges
        # These groups form the outside-in borders i.e. multiple
        # for multiple borders
        if width == 0:
            self.destroy_borders(window, tree)
            return

        if len(colors) > width:
            colors = colors[:width]

        num = len(colors)

        # We can re-use old border nodes, but let's get rid of any extras.
        borders = []
        for ptr in wl_list_for_each(
            "struct wlr_scene_node *", tree._ptr.children, "link", ffi=ffi
        ):
            node = SceneNode(ptr)
            if node.type == SceneNodeType.RECT:
                # TODO: hopefully SceneRect(ptr=...) will be merged into pywlroots
                # rect_ptr = wl_container_of(ptr, "struct wlr_scene_rect *", "node", ffi=ffi)
                # borders.append(SceneRect(ptr=rect_ptr))
                borders.append(node)

        for node in borders[num * 4 :]:
            node.destroy()
        borders = borders[: num * 4]

        widths = [width // num] * num
        for i in range(width % num):
            widths[i] += 1

        outer_w = window.width + width * 2
        outer_h = window.height + width * 2
        coord = 0

        for i, color in enumerate(colors):
            color_ = _rgb(color)
            bw = widths[i]

            # [x, y, width, height] for N, E, S, W
            geometries = (
                (coord, coord, outer_w - coord * 2, bw),
                (outer_w - bw - coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
                (coord, outer_h - bw - coord, outer_w - coord * 2, bw),
                (coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
            )

            rects = borders[:4]
            borders = borders[4:]
            for i, (x, y, w, h) in enumerate(geometries):
                try:
                    node = rects[i]
                    rect_ptr = wl_container_of(
                        node._ptr, "struct wlr_scene_rect *", "node", ffi=ffi
                    )
                    lib.wlr_scene_rect_set_color(rect_ptr, color_)
                    lib.wlr_scene_rect_set_size(rect_ptr, w, h)
                    node.set_position(x, y)
                    # TODO: see above
                    # rect = rects[i]
                    # rect.set_color(color_)
                    # rect.set_size(w, h)
                    # rect.node.set_position(x, y)
                except IndexError:
                    rect = SceneRect(tree, w, h, color_)
                    rect.node.set_position(x, y)

            coord += bw

    def destroy_borders(self, window: WindowType, tree: SceneTree) -> None:
        for ptr in list(
            wl_list_for_each("struct wlr_scene_node *", tree._ptr.children, "link", ffi=ffi)
        ):
            node = SceneNode(ptr)
            if node.type == SceneNodeType.RECT:
                node.destroy()

    def render(self, output: Output) -> None:
        """Render the scene graph to [output]."""
        # wlroots does all the work
        output.scene_output.commit()
