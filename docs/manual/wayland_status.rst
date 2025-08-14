===================================
Current Wayland Situation in Qtile
===================================

.. _wayland_status:

A lot of people have been asking about the current status of Qtile's Wayland backend.
Questions like:

- "Why is Qtile stuck on ``wlroots 0.17.0``?"
- "When will feature X be implemented?"

Instead of answering individually, this write-up should clarify things for everyone.

----

A Look Back
===========

.. _look_back:

Qtile's Wayland backend has been built on `pywlroots <https://github.com/flacjacket/pywlroots>`_ since day one — a Python binding to the ``wlroots`` library via ``cffi``.

It served us decently for a while, but over time, its limitations started to outweigh the benefits.

Why pywlroots became a problem
------------------------------

1. **Stalled Development**  

- ``pywlroots`` hasn't had a release since **May 13, 2024**, and `Jwijenbergh <https://github.com/jwijenbergh>`_ (a Qtile maintainer and the lead dev on the Wayland side) had to take over maintenance.

2. **No Direct Access to Wlroots**

- Less control over low-level behavior.
- Inefficient resource handling compared to working directly in C.

3. **Maintenance Nightmare**

- Track upstream ``wlroots`` changes.
- Update the Python bindings.
- Translate C semantics to Python.
- Update Qtile's Python side to use new APIs.

  **It's a constant uphill battle.**

4. **Blocked Features**  

Key features like **gamma control** can't be implemented cleanly due to wrapper limitations.  
→ See: `Issue #5239 <https://github.com/qtile/qtile/issues/5239>`_

----

The New Path
============

.. _new_path:

Maintaining the Wayland backend this way became **unsustainable**. So **Jwijenbergh** proposed something bold:

- **Rewriting the Wayland backend in C with direct access to `wlroots`.**

This would:

- **Improve performance.**
- **Allow tighter integration.**
- **Make updates easier.**
- **Cut out the middleman (`pywlroots`).**

This change also makes Qtile's backend more future-proof and aligns it closer to what other compositors like sway or river do.

Relevant discussion: `Qtile Wayland Issues <https://github.com/qtile/qtile/issues?q=is%3Aissue+wayland>`_

From Discord (tl;dr)
---------------------

.. code-block:: text

    @Jwijenbergh: im currently rewriting the wayland backend in C ...
    @Sigmanificient: OH, i absolutely love C, i would love to help you on this
    @Jwijenbergh: ok I will push a branch tomorrow
    @Jwijenbergh: it's a lot of work and I don't have a lot of time 
    @Gurjaka: c or cython?
    @Jwijenbergh: c
    ...
    @Gurjaka: So you are doing what hyprland did? Going independent from wlroots?
    @Jwijenbergh: no, just writing the compositor part in C with wlroots, without pywlroots

----

Current Status
==============

.. _current_status:

We've started working on this in a dedicated branch:  
`wayc <https://github.com/qtile/qtile/tree/wayc>`_ in the main Qtile repo.

To check wayc progression visit:
`wayc backend development <https://github.com/orgs/qtile/projects/7/views/1>`_ in Qtile projects.

How You Can Help
================

.. _how_you_can_help:

This is a **big task**, and we've made huge strides as a small team — learning Wayland, improving together, and pushing boundaries.

If you're interested in contributing to **WayC**, join us!

- `Qtile Contribution Guide <https://docs.qtile.org/en/stable/manual/contributing.html#>`_
- `Recommended Resources for Getting Started with Wayland Development <https://docs.qtile.org/en/latest/manual/contributing.html#recommended-resources-for-getting-started-with-wayland-development>`_
- `Discord channel for discussions <https://discord.gg/ehh233wCrC>`_

Even if you're new to C or Wayland, this is a great chance to grow and work on something meaningful in open source.
