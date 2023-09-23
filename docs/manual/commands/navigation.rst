.. _object_graph_selectors:

Navigating the command graph
============================

As noted previously, some objects require a selector to ensure that the correct
object is selected, while other nodes provide a default object without a selector.

The table below shows what selectors are required for the diferent nodes and whether
the selector is optional (i.e. if it can be omitted to select the default object).

.. list-table::
    :widths: 15 30 15 40
    :header-rows: 1

    * - Object
      - Key
      - Optional?
      - Example
    * - :doc:`bar <api/bars>`
      - | "top", "bottom"
        | (Note: if accessing this node from the root, users on multi-monitor
          setups may wish to navigate via a ``screen`` node to ensure that they
          select the correct object.)
      - No
      - | c.screen.bar["bottom"]
    * - :doc:`group <api/groups>`
      - Name string
      - Yes
      - | c.group["one"]
        | c.group
    * - :doc:`layout <api/layouts>`
      - Integer index
      - Yes
      - | c.layout[2]
        | c.layout
    * - :doc:`screen <api/screens>`
      - Integer index
      - Yes
      - | c.screen[1]
        | c.screen
    * - :doc:`widget <api/widgets>`
      - | Widget name
        | (This is usually the name of the widget class in lower case but can
          be set by passing the ``name`` parameter to the widget.)
      - No
      - | c.widget["textbox"]
    * - :doc:`window <api/windows>`
      - Integer window ID
      - Yes
      - | c.window[123456]
        | c.window
    * - :doc:`core <api/backend>`
      - No
      - n/a
      - | c.core
