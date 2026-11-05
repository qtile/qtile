import ast

import pytest

from libqtile import bar, config, layout, widget
from libqtile.confreader import Config
from libqtile.core.state import QtileState
from libqtile.resources import default_config
from libqtile.screen_group_policy import ScreenGroupPreferences, swap_screen_groups
from test.helpers import Retry


class RecordingPolicy:
    def __init__(self, policy=None):
        self.policy = policy if policy is not None else ScreenGroupPreferences()
        self.requests = []
        self.contexts = []

    def __call__(self, context, request):
        self.contexts.append(context)
        self.requests.append(request)
        return self.policy(context, request)


def policy_config(count=2, policy=None):
    class PolicyConfig(Config):
        groups = [config.Group(str(index)) for index in range(1, 5)]
        layouts = [layout.Max()]
        floating_layout = default_config.floating_layout
        keys = []
        mouse = []
        follow_mouse_focus = False
        cursor_warp = False
        reconfigure_screens = False
        screens = []
        fake_screens = [
            config.Screen(
                top=bar.Bar([widget.GroupBox()], 20),
                x=index * 250,
                y=0,
                width=250,
                height=550,
            )
            for index in range(count)
        ]
        screen_group_policy = RecordingPolicy(policy)

    return PolicyConfig


def default_policy_config(setting="default", count=2):
    conf = policy_config(count=count)
    if setting == "default":
        del conf.screen_group_policy
    elif setting == "wrapped":
        conf.screen_group_policy = staticmethod(
            lambda context, request: swap_screen_groups(context, request)
        )
    else:
        conf.screen_group_policy = staticmethod(swap_screen_groups)
    return conf


def assignments(manager):
    manager.groupconsistency()
    return [screen["group"] for screen in manager.c.get_screens()]


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_assignments(manager, expected):
    assert assignments(manager) == expected


def evaluate(manager, expression):
    return ast.literal_eval(manager.c.eval(expression))


def priority(manager):
    return evaluate(manager, "self.config.screen_group_policy.policy.priority")


def preferences(manager):
    return evaluate(manager, "self.config.screen_group_policy.policy.preferences")


def last_request(manager):
    return evaluate(
        manager,
        "[None if request is None else (request.monitor_id, request.group_name) "
        "for request in self.config.screen_group_policy.requests][-1]",
    )


def test_selection_restoration_focus_and_reselection(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    assert assignments(manager) == ["1", "2"]

    manager.c.group["1"].toscreen(1)
    assert assignments(manager) == ["2", "1"]
    assert priority(manager) == ["screen:1", "screen:0"]

    manager.c.to_screen(1)
    manager.c.to_screen(0)
    assert priority(manager) == ["screen:1", "screen:0"]
    assert manager.c.eval("self.current_screen.index") == "0"

    manager.c.group["3"].toscreen(1)
    assert assignments(manager) == ["1", "3"]
    assert manager.c.eval("self.current_screen.index") == "0"
    assert manager.c.eval("self.screens[0].previous_group is None") == "True"

    manager.c.group["1"].toscreen(0)
    assert assignments(manager) == ["1", "3"]
    assert priority(manager) == ["screen:0", "screen:1"]


def test_displaced_group_resets_focus_history_and_warps_when_focused(manager_nospawn):
    conf = default_policy_config()
    conf.cursor_warp = True
    manager = manager_nospawn
    manager.start(conf)
    manager.test_window("warp-window")
    wid = manager.c.window.info()["id"]
    assert (
        manager.c.eval(f"self.groups_map['1'].last_focused is self.windows_map[{wid}]") == "True"
    )

    manager.c.group["2"].toscreen(0)
    assert assignments(manager) == ["2", "1"]
    assert manager.c.eval("self.groups_map['1'].last_focused is None") == "True"

    manager.c.eval("self.core.warp_pointer(10, 30)")
    manager.c.to_screen(1)
    assert manager.c.window.info()["id"] == wid
    info = manager.c.window.info()
    expected = (info["x"] + info["width"] // 2, info["y"] + info["height"] // 2)

    @Retry(ignore_exceptions=(AssertionError,))
    def pointer_is_centered():
        assert evaluate(manager, "self.core.get_mouse_position()") == expected

    pointer_is_centered()


def test_screen_and_groupbox_commands_record_selection(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    manager.c.to_screen(1)
    manager.c.screen.next_group(warp=False)
    assert assignments(manager) == ["1", "3"]
    assert last_request(manager) == ("screen:1", "3")

    manager.c.screen.prev_group(warp=False)
    assert assignments(manager) == ["1", "2"]
    manager.c.screen.toggle_group("3", warp=False)
    assert assignments(manager) == ["1", "3"]
    manager.c.screen.toggle_group(warp=False)
    assert assignments(manager) == ["1", "2"]

    manager.c.widget["groupbox_1"].eval("self.go_to_group(self.qtile.groups_map['1'])")
    assert assignments(manager) == ["2", "1"]
    assert last_request(manager) == ("screen:1", "1")
    manager.c.widget["groupbox_1"].eval("self.next_group()")
    assert assignments(manager) == ["1", "2"]
    assert last_request(manager) == ("screen:1", "2")


def test_screen_set_group_records_selection(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    manager.c.eval("self.screens[1].set_group(self.groups_map['1'])")
    assert assignments(manager) == ["2", "1"]
    assert last_request(manager) == ("screen:1", "1")
    assert priority(manager) == ["screen:1", "screen:0"]


def test_move_and_follow_records_selection_including_same_group(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    manager.test_window("policy-window")
    wid = manager.c.window.info()["id"]
    manager.c.window[wid].togroup("3", switch_group=True)
    assert assignments(manager) == ["3", "2"]
    assert manager.c.window[wid].info()["group"] == "3"
    assert last_request(manager) == ("screen:0", "3")

    manager.c.to_screen(1)
    manager.c.window[wid].togroup("3", switch_group=True)
    assert assignments(manager) == ["1", "3"]
    assert last_request(manager) == ("screen:1", "3")
    assert manager.c.window[wid].info()["group"] == "3"


@pytest.mark.parametrize("setting", ["default", "builtin", "wrapped"])
def test_swap_policy_follows_same_group_selection(manager_nospawn, setting):
    conf = default_policy_config(setting)
    manager = manager_nospawn
    manager.start(conf)
    manager.test_window("same-group-window")
    wid = manager.c.window.info()["id"]

    manager.c.to_screen(1)
    manager.c.window[wid].togroup("1", switch_group=True)

    assert assignments(manager) == ["2", "1"]
    assert manager.c.eval("self.current_screen.index") == "1"
    assert manager.c.window[wid].info()["group"] == "1"


@pytest.mark.parametrize("setting", ["default", "builtin", "wrapped"])
def test_swap_policy_initial_assignments_honor_screen_affinity(manager_nospawn, setting):
    conf = default_policy_config(setting)
    conf.groups = [
        config.Group("1", screen_affinity=0),
        config.Group("2", screen_affinity=0),
        config.Group("3", screen_affinity=1),
        config.Group("4", screen_affinity=1),
    ]
    manager_nospawn.start(conf)
    assert assignments(manager_nospawn) == ["1", "3"]


@pytest.mark.parametrize("affinity", [0, 1])
def test_swap_policy_creates_a_group_when_no_affinity_matches(manager_nospawn, affinity):
    conf = default_policy_config()
    conf.groups = [config.Group(name, screen_affinity=affinity) for name in ("1", "2")]
    manager_nospawn.start(conf)
    displayed = assignments(manager_nospawn)
    assert displayed[affinity] == "1"
    assert displayed[1 - affinity].startswith("autogen_")


@pytest.mark.parametrize("setting", ["default", "builtin", "wrapped"])
def test_swap_policy_notifications_and_no_preference_restoration(manager_nospawn, setting):
    manager = manager_nospawn
    manager.start(default_policy_config(setting))
    manager.c.eval(
        "self.policy_layouts = []\n"
        "self.policy_notifications = []\n"
        "def layout_changed(layout, group, qtile=self):\n"
        "    qtile.policy_layouts.append(group.name)\n"
        "    qtile.policy_notifications.append('layout_change')\n"
        "hook.subscribe.layout_change(layout_changed)\n"
        "hook.subscribe.setgroup(lambda qtile=self: "
        "qtile.policy_notifications.append('setgroup'))\n"
        "hook.subscribe.focus_change(lambda qtile=self: "
        "qtile.policy_notifications.append('focus_change'))"
    )

    manager.c.group["1"].toscreen(1)
    assert assignments(manager) == ["2", "1"]
    assert evaluate(manager, "self.policy_layouts") == ["1"]
    assert evaluate(manager, "self.policy_notifications") == [
        "setgroup",
        "focus_change",
        "layout_change",
    ]

    manager.c.group["1"].toscreen(1)
    assert evaluate(manager, "self.policy_notifications") == [
        "setgroup",
        "focus_change",
        "layout_change",
    ]
    manager.c.group["4"].toscreen(1)
    assert assignments(manager) == ["2", "4"]
    manager.c.reconfigure_screens()
    assert assignments(manager) == ["2", "4"]
    assert manager.c.eval("self.screens[0].previous_group is None") == "True"


def test_default_policy_hooks_can_request_another_group(manager_nospawn):
    manager = manager_nospawn
    manager.start(default_policy_config())
    manager.c.eval(
        "self.policy_notifications = []\n"
        "def record(event, group=None, qtile=self):\n"
        "    qtile.policy_notifications.append((event, "
        "[screen.group.name for screen in qtile.screens], group))\n"
        "def followup(qtile=self, record=record):\n"
        "    record('setgroup')\n"
        "    if qtile.current_group.name == '3':\n"
        "        qtile.groups_map['4'].toscreen()\n"
        "hook.subscribe.setgroup(followup)\n"
        "hook.subscribe.focus_change(lambda record=record: record('focus_change'))\n"
        "hook.subscribe.layout_change(lambda layout, group, record=record: "
        "record('layout_change', group.name))"
    )
    manager.c.group["3"].toscreen(0)
    wait_for_assignments(manager, ["4", "2"])
    assert manager.c.eval("self._group_change_phase") == "idle"
    assert evaluate(manager, "self.policy_notifications") == [
        ("setgroup", ["3", "2"], None),
        ("focus_change", ["3", "2"], None),
        ("layout_change", ["3", "2"], "3"),
        ("setgroup", ["4", "2"], None),
        ("focus_change", ["4", "2"], None),
        ("layout_change", ["4", "2"], "4"),
    ]


@pytest.mark.parametrize("requester_is_current", [True, False])
@pytest.mark.parametrize("callback_target", [0, 1])
def test_client_focus_selection_is_queued_until_assignment_completes(
    manager_nospawn, callback_target, requester_is_current
):
    manager = manager_nospawn
    manager.start(default_policy_config())
    for index in range(2):
        manager.c.to_screen(index)
        manager.test_window(f"swap-{index + 1}")
    manager.c.to_screen(0 if requester_is_current else 1)
    focus_name = "swap-2" if requester_is_current else "swap-1"
    manager.c.eval(
        "self.policy_observations = []\n"
        "self.policy_followup_requested = False\n"
        f"self.policy_followup_target = {callback_target}\n"
        f"self.policy_followup_name = {focus_name!r}\n"
        "def observe(event, qtile=self):\n"
        "    consistent = all(screen.group.screen is screen for screen in qtile.screens)\n"
        "    consistent = consistent and all(group.screen is None or "
        "group.screen.group is group for group in qtile.groups)\n"
        "    qtile.policy_observations.append((event, "
        "[screen.group.name for screen in qtile.screens], consistent))\n"
        "def followup(client, qtile=self, record=observe):\n"
        "    record('client_focus')\n"
        "    if client.name == qtile.policy_followup_name and not "
        "qtile.policy_followup_requested:\n"
        "        qtile.policy_followup_requested = True\n"
        "        qtile.groups_map['3'].toscreen(qtile.policy_followup_target)\n"
        "hook.subscribe.client_focus(followup)\n"
        "hook.subscribe.setgroup(lambda record=observe: record('setgroup'))"
    )

    manager.c.group["2"].toscreen(0)
    expected = ["3", "1"] if callback_target == 0 else ["2", "3"]
    wait_for_assignments(manager, expected)
    assert manager.c.eval("self.policy_followup_requested") == "True"
    assert manager.c.eval("self._group_change_phase") == "idle"
    observations = evaluate(manager, "self.policy_observations")
    assert observations
    assert all(consistent for _, _, consistent in observations)
    assert [mapping for event, mapping, _ in observations if event == "setgroup"] == [
        ["2", "1"],
        expected,
    ]
    assert {window["name"]: window["group"] for window in manager.c.windows()} == {
        "swap-1": "1",
        "swap-2": "2",
    }


def test_custom_policy_cannot_recursively_select_groups(manager_nospawn):
    def policy(context, request):
        if request is not None:
            from libqtile import qtile

            qtile.groups_map["4"].toscreen()
        return swap_screen_groups(context, request)

    manager = manager_nospawn
    manager.start(policy_config(policy=policy))
    manager.c.group["3"].toscreen(0)
    assert assignments(manager) == ["3", "2"]
    assert evaluate(
        manager,
        "[None if request is None else (request.monitor_id, request.group_name) "
        "for request in self.config.screen_group_policy.requests]",
    ) == [None, ("screen:0", "3")]
    assert manager.c.eval("self._group_change_phase") == "idle"


@pytest.mark.parametrize("setting", ["default", "builtin", "wrapped"])
def test_default_policy_repairs_deleted_group_references(manager_nospawn, setting):
    manager = manager_nospawn
    manager.start(default_policy_config(setting))
    manager.c.group["3"].toscreen(1)
    assert manager.c.eval("self.screens[1].previous_group.name") == "2"
    manager.c.eval("self.delete_group('2')")
    assert manager.c.eval("self.screens[1].previous_group is None") == "True"
    manager.c.eval("self.delete_group('3')")
    assert assignments(manager) == ["1", "4"]
    assert manager.c.eval("self.current_screen.index") == "0"


def test_application_and_script_requests_promote_only_their_target(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    initial_preferences = preferences(manager)
    manager.c.eval("self.screens[1].set_group(self.groups_map['1'])")
    assert assignments(manager) == ["2", "1"]
    assert last_request(manager) == ("screen:1", "1")
    assert priority(manager) == ["screen:1", "screen:0"]
    first_preferences = preferences(manager)
    assert first_preferences["screen:0"] == initial_preferences["screen:0"]
    assert first_preferences["screen:1"] == ["1", "2", "3", "4"]

    manager.c.eval("self.current_screen.set_group(self.groups_map['4'])")
    assert assignments(manager) == ["4", "1"]
    assert last_request(manager) == ("screen:0", "4")
    assert priority(manager) == ["screen:0", "screen:1"]
    second_preferences = preferences(manager)
    assert second_preferences["screen:0"] == ["4", "1", "2", "3"]
    assert second_preferences["screen:1"] == first_preferences["screen:1"]

    if manager.backend.name == "x11":
        manager.c.eval(
            "from types import SimpleNamespace\n"
            "event = SimpleNamespace(type=self.core.conn.atoms['_NET_CURRENT_DESKTOP'], "
            "data=SimpleNamespace(data32=[2]))\n"
            "self.core.handle_ClientMessage(event)"
        )
    else:
        manager.c.eval("self.core.handle_workspace_manager_group_activate('3')")
    assert assignments(manager) == ["3", "1"]
    assert last_request(manager) == ("screen:0", "3")
    assert priority(manager) == ["screen:0", "screen:1"]
    final_preferences = preferences(manager)
    assert final_preferences["screen:0"] == ["3", "4", "1", "2"]
    assert final_preferences["screen:1"] == second_preferences["screen:1"]
    assert manager.c.eval("self.current_screen.previous_group.name") == "4"

    manager.c.reconfigure_screens()
    assert assignments(manager) == ["3", "1"]
    assert last_request(manager) is None
    assert preferences(manager) == final_preferences
    assert priority(manager) == ["screen:0", "screen:1"]
    assert manager.c.eval("self.current_screen.previous_group.name") == "4"


@pytest.mark.parametrize("restored_groups", [[], [("5", "max", "5")]])
def test_startup_policy_sees_restored_state(manager_nospawn, restored_groups):
    state = QtileState.__new__(QtileState)
    state.groups = restored_groups
    state.screens = {0: "3", 1: "4"}
    state.current_screen = 1
    state.scratchpads = {}
    state.orphans = []
    state.restart = True
    manager_nospawn.start(policy_config(), state=state)

    assert assignments(manager_nospawn) == ["3", "4"]
    assert evaluate(
        manager_nospawn,
        "[monitor.group for monitor in self.config.screen_group_policy.contexts[0].monitors]",
    ) == ["3", "4"]
    assert evaluate(
        manager_nospawn,
        "self.config.screen_group_policy.requests",
    ) == [None]
    assert manager_nospawn.c.eval("self.current_screen.index") == "1"


def test_policy_assigns_initial_groups_once_screens_are_registered(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    assert evaluate(
        manager,
        "[monitor.group for monitor in self.config.screen_group_policy.contexts[0].monitors]",
    ) == [None, None]
    assert evaluate(manager, "self.config.screen_group_policy.requests") == [None]
    assert assignments(manager) == ["1", "2"]


@pytest.mark.parametrize(
    "failure", ["duplicate", "missing", "unknown", "scratchpad", "exception", "none"]
)
def test_invalid_policies_fall_back_without_partial_assignment(manager_nospawn, failure):
    def policy(context, request):
        if request is None:
            return swap_screen_groups(context, request)
        if failure == "none":
            return None
        if failure == "exception":
            raise RuntimeError("intentional policy failure")
        mapping = {monitor.id: context.groups[2] for monitor in context.monitors}
        if failure == "missing":
            mapping.pop(context.monitors[1].id)
        elif failure == "unknown":
            mapping[context.monitors[1].id] = "missing-group"
        elif failure == "scratchpad":
            mapping[context.monitors[1].id] = "scratch"
        return mapping

    manager = manager_nospawn
    conf = policy_config(policy=policy)
    conf.groups.append(config.ScratchPad("scratch", []))
    manager.start(conf)
    assert evaluate(manager, "self.config.screen_group_policy.contexts[0].groups") == (
        "1",
        "2",
        "3",
        "4",
    )
    manager.c.group["3"].toscreen(1)
    assert assignments(manager) == ["1", "3"]
    assert manager.c.eval("self.screens[0].previous_group is None") == "True"
    assert manager.c.eval("self.screens[1].previous_group.name") == "2"
    assert "screen_group_policy failed" in manager._drain_logs()


def test_three_cycle_has_one_hook_with_complete_bidirectional_mapping(manager_nospawn):
    def rotate(context, request):
        if request is None:
            return swap_screen_groups(context, request)
        return {
            monitor.id: context.groups[(index + 1) % len(context.monitors)]
            for index, monitor in enumerate(context.monitors)
        }

    manager = manager_nospawn
    manager.start(policy_config(count=3, policy=rotate))
    for index in range(3):
        manager.c.to_screen(index)
        manager.test_window(f"cycle-{index + 1}", floating=index == 1)
    windows = {window["name"]: window["id"] for window in manager.c.windows()}
    manager.c.to_screen(0)
    manager.c.eval(
        "self.test_data = []\n"
        "self.policy_layouts = []\n"
        "def record_assignment(event, qtile=self):\n"
        "    qtile.test_data.append((event, "
        "[screen.group.name for screen in qtile.screens], "
        "all(screen.group.screen is screen for screen in qtile.screens)))\n"
        "def layout_changed(layout, group, qtile=self, record=record_assignment):\n"
        "    qtile.policy_layouts.append(group.name)\n"
        "    record('layout_change')\n"
        "hook.subscribe.setgroup(lambda record=record_assignment: record('setgroup'))\n"
        "hook.subscribe.focus_change(lambda record=record_assignment: record('focus_change'))\n"
        "hook.subscribe.layout_change(layout_changed)\n"
        "hook.subscribe.client_focus(lambda client, record=record_assignment: "
        "record('client_focus'))"
    )
    manager.c.group["4"].toscreen(0)
    assert assignments(manager) == ["2", "3", "1"]
    observations = evaluate(manager, "self.test_data")
    events = [event for event, _, _ in observations]
    for event in ("setgroup", "focus_change", "layout_change", "client_focus"):
        assert events.count(event) == 1
    assert evaluate(manager, "self.policy_layouts") == ["2"]
    assert all(
        mapping == ["2", "3", "1"] and consistent for _, mapping, consistent in observations
    )
    for group_name in ("1", "2", "3"):
        assert manager.c.window[windows[f"cycle-{group_name}"]].info()["group"] == group_name
    assert manager.c.window.info()["name"] == "cycle-2"


def test_hotplug_and_reordering_use_monitor_identity(manager_nospawn, monkeypatch):
    def outputs(core):
        names = getattr(core, "policy_test_outputs", ("A", "B"))
        connector_suffix = getattr(core, "policy_test_connector_suffix", "")
        return [
            config.Output(
                f"DP-{name}{connector_suffix}",
                "Test",
                "Monitor",
                name,
                config.ScreenRect(index * 300, 0, 300, 550),
            )
            for index, name in enumerate(names)
        ]

    conf = policy_config()
    conf.fake_screens = None
    conf.generate_screens = staticmethod(lambda outputs: [config.Screen() for _ in outputs])
    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", outputs
    )
    manager = manager_nospawn
    manager.start(conf)
    manager.c.group["1"].toscreen(1)
    manager.c.to_screen(1)
    assert assignments(manager) == ["2", "1"]

    manager.c.eval("self.core.policy_test_outputs = ('A',)")
    manager.c.reconfigure_screens()
    assert assignments(manager) == ["1"]
    assert manager.c.eval("self.current_screen is self.screens[0]") == "True"

    manager.c.eval(
        "self.core.policy_test_outputs = ('B', 'A')\n"
        "self.core.policy_test_connector_suffix = '-reconnected'"
    )
    manager.c.reconfigure_screens()
    assert assignments(manager) == ["1", "2"]
    assert manager.c.screen[0].info()["serial"] == "B"
    assert priority(manager) == ["serial:Test:Monitor:B", "serial:Test:Monitor:A"]


@pytest.mark.parametrize("initially_connected", [True, False])
def test_no_outputs_keep_a_valid_fallback_and_restore_preferences(
    manager_nospawn, monkeypatch, initially_connected
):
    def outputs(core):
        names = getattr(core, "policy_test_outputs", ("A", "B") if initially_connected else ())
        return [
            config.Output(
                f"DP-{name}",
                "Test",
                "Monitor",
                name,
                config.ScreenRect(index * 300, 0, 300, 550),
            )
            for index, name in enumerate(names)
        ]

    conf = policy_config()
    conf.fake_screens = None
    conf.generate_screens = staticmethod(lambda outputs: [config.Screen() for _ in outputs])
    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", outputs
    )
    manager = manager_nospawn
    manager.start(conf)
    if initially_connected:
        manager.c.group["1"].toscreen(1)
        manager.c.to_screen(1)
        assert assignments(manager) == ["2", "1"]
        manager.c.eval("self.core.policy_test_outputs = ()")
        manager.c.reconfigure_screens()

    fallback = manager.c.get_screens()
    assert len(fallback) == 1
    assert fallback[0]["index"] == 0
    assert fallback[0]["width"] > 0
    assert fallback[0]["height"] > 0
    assert assignments(manager) == ["1"]
    assert manager.c.eval("self.current_screen is self.screens[0]") == "True"
    assert manager.c.eval("self.screens[0].qtile is self") == "True"

    manager.c.eval("self.core.policy_test_outputs = ('A', 'B')")
    manager.c.reconfigure_screens()
    assert assignments(manager) == (["2", "1"] if initially_connected else ["1", "2"])
    assert [manager.c.screen[index].info()["serial"] for index in range(2)] == ["A", "B"]


def test_no_outputs_without_groups_creates_a_configured_fallback(manager_nospawn, monkeypatch):
    conf = policy_config()
    conf.groups = []
    conf.fake_screens = None
    conf.generate_screens = staticmethod(lambda outputs: [])
    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info",
        lambda core: [],
    )
    manager_nospawn.start(conf)
    assert assignments(manager_nospawn) == ["autogen_1"]
    assert manager_nospawn.c.eval("self.current_screen is self.screens[0]") == "True"
    assert manager_nospawn.c.eval("self.screens[0].qtile is self") == "True"


def test_delete_displayed_group_on_other_screen_and_add_group(manager_nospawn):
    manager = manager_nospawn
    manager.start(policy_config())
    manager.c.group["3"].toscreen(0)
    manager.c.group["1"].toscreen(0)
    assert manager.c.eval("self.screens[0].previous_group.name") == "3"
    manager.c.group["3"].toscreen(1)
    assert assignments(manager) == ["1", "3"]
    manager.c.delgroup("3")
    assert assignments(manager) == ["1", "2"]
    assert "3" not in manager.c.get_groups()
    assert manager.c.eval("self.screens[0].previous_group is None") == "True"
    assert last_request(manager) is None

    manager.c.addgroup("5", persist=True)
    assert last_request(manager) is None
    manager.c.group["5"].toscreen(1)
    assert assignments(manager) == ["1", "5"]


@pytest.mark.parametrize("screen", [0, 1])
def test_deleting_displayed_treetab_group_hides_its_panel(manager_nospawn, screen):
    conf = default_policy_config()
    conf.layouts = [layout.Max(), layout.TreeTab()]
    conf.groups[0] = config.Group("1", layout="treetab")
    manager = manager_nospawn
    manager.start(conf)
    manager.c.group["1"].toscreen(screen)
    manager.c.eval("self.deleted_panel = self.groups_map['1'].layout._panel")
    if manager.backend.name == "x11":
        visible = "not self.deleted_panel.hidden"
    else:
        manager.c.eval(
            "from libqtile.backend.wayland._ffi import lib\nself.policy_test_wayland_lib = lib"
        )
        visible = "self.policy_test_wayland_lib.qw_view_is_visible(self.deleted_panel._ptr)"
    assert evaluate(manager, visible)

    manager.c.delgroup("1")

    assert not evaluate(manager, visible)
    assert "1" not in assignments(manager)
