# Mouse

The `mouse` config file variable defines a set of global mouse actions, and
is a list of [`libqtile.config.Click`] and [`libqtile.config.Drag`][]
objects, which define what to do when a window is clicked or dragged.

## Default Mouse Bindings

By default, holding your `mod` key and left-clicking (and holding) a window will
allow you to drag it around as a floating window. Holding your `mod` key and right-clicking
(and holding) a window will resize the window (and also make it float if it is not already floating).

## Example

```python
from libqtile.config import Click, Drag
mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
        start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
        start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front())
]
```

The above example can also be written more concisely with the help of
the `EzClick` and `EzDrag` helpers:

```python
from libqtile.config import EzClick as Click, EzDrag as Drag

mouse = [
    Drag("M-1", lazy.window.set_position_floating(),
        start=lazy.window.get_position()),
    Drag("M-3", lazy.window.set_size_floating(),
        start=lazy.window.get_size()),
    Click("M-2", lazy.window.bring_to_front())
]
```

## Reference

::: libqtile.config.Click
    options:
      heading_level: 3

::: libqtile.config.Drag
    options:
      heading_level: 3

::: libqtile.config.EzClick
    options:
      heading_level: 3
