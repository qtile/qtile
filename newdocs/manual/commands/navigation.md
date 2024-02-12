# Navigating the command graph

As noted previously, some objects require a selector to ensure that the correct
object is selected, while other nodes provide a default object without a selector.

The table below shows what selectors are required for the diferent nodes and whether
the selector is optional (i.e. if it can be omitted to select the default object).

Object | Key | Optional? | Example
------ | --- | --------- | -------
[`bar`][libqtile.bars] | `"top"`, `"bottom"`[^1] | No | `c.screen.bar["bottom"]`
[`group`][libqtile.groups] | Name string | Yes | `c.group["one"]`<br>`c.group`
[`layout`][libqtile.layouts] | Integer index | Yes | `c.layout[2]`<br>`c.layout`
[`screen`][libqtile.screens] | Integer index | Yes | `c.screen[1]`<br>`c.screen`
[`widget`][libqtile.widgets] | Widget name[^2] | No | `c.widget["textbox"]`
[`window`][libqtile.windows] | Integer window ID | Yes | `c.window[123456]`<br>`c.window`
[`core`][libqtile.backend] | No | n/a | `c.core`

[^1]:
  If accessing this node from the root, users on multi-monitor
  setups may wish to navigate via a `screen` node to ensure that they
  select the correct object.

[^2]:
  This is usually the name of the widget class in lower case but can
  be set by passing the `name` parameter to the widget.