===================================
Current Wayland Situation in Qtile
===================================

.. _wayland_status:

Often, we get questions what the status is of the Wayland backend. Understandably so, as we were previously stuck on an old Wlroots (the Wayland library we use) version for quite some time.

To ease the development of the Wayland backend and implement new Wlroots versions faster, the Wayland backend has previously been rewritten from Python to C. This additionally, should improve performance in certain areas. The downside of this approach is that the backend is written in two programming languages now and we have to have some glue in between. However, this tradeoff is worth it as it is (on the long-term) quicker than updating the Python Wlroots bindings every time a new Wlroots version is released.

The goal of the backend is the following:
- Move as much Wayland specifics to C
- Keep the Qtile specific stuff in Python: layouts, config, window states (floating, tiled etc)
- Explore new features by now being written in C

The status of this backend can be viewed on GitHub:
- `Wayland GitHub Project Board <https://github.com/orgs/qtile/projects/2>`_

To help contributing to this backend there are some useful links:
- `Qtile Contribution Guide <https://docs.qtile.org/en/stable/manual/contributing.html#>`_
- `Recommended Resources for Getting Started with Wayland Development <https://docs.qtile.org/en/latest/manual/contributing.html#recommended-resources-for-getting-started-with-wayland-development>`_
- `Discord channel for discussions <https://discord.gg/ehh233wCrC>`_

Even if you're new to C or Wayland, this is a great chance to grow and work on something meaningful in open source.
