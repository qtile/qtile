import textwrap


def test_popup_focus(manager):
    manager.test_window("one")
    start_wins = len(manager.backend.get_all_windows())

    manager.c.eval(
        textwrap.dedent(
            """
        from libqtile.popup import Popup
        popup = Popup(self,
            x=0,
            y=0,
            width=self.current_screen.width,
            height=self.current_screen.height,
        )
        popup.place()
        popup.unhide()
    """
        )
    )

    end_wins = len(manager.backend.get_all_windows())
    assert end_wins == start_wins + 1

    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.group.info()["windows"] == ["one"]
    assert len(manager.c.windows()) == 1
