from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from libqtile.screen_group_policy import (
    ScreenGroupContext,
    ScreenGroupMonitor,
    ScreenGroupPreferences,
    ScreenGroupRequest,
    get_monitor_ids,
    swap_screen_groups,
)


def context(assignments=(("A", "1"), ("B", "2")), groups=("1", "2", "3"), group_affinities=()):
    return ScreenGroupContext(
        tuple(
            ScreenGroupMonitor(monitor_id, index, None, None, None, None, group)
            for index, (monitor_id, group) in enumerate(assignments)
        ),
        groups,
        group_affinities,
    )


def select(monitor_id, group_name):
    return ScreenGroupRequest(monitor_id, group_name)


def output_screen(port=None, make=None, model=None, serial=None):
    return SimpleNamespace(
        output=SimpleNamespace(port=port, make=make, model=model, serial=serial)
    )


def test_policy_inputs_are_immutable():
    snapshot = context()
    request = select("B", "1")
    with pytest.raises(FrozenInstanceError):
        snapshot.groups = ("changed",)
    with pytest.raises(FrozenInstanceError):
        snapshot.group_affinities = (("changed", 0),)
    with pytest.raises(FrozenInstanceError):
        snapshot.monitors[0].group = "changed"
    with pytest.raises(FrozenInstanceError):
        request.monitor_id = "changed"
    with pytest.raises(FrozenInstanceError):
        request.group_name = "changed"


def test_monitor_ids_prefer_serial_and_ignore_connector_and_screen_order():
    a = output_screen("HDMI-1", "Dell", "U2723QE", "A")
    b = output_screen("DP-1", "Dell", "U2723QE", "B")
    assert get_monitor_ids([a, b]) == ("serial:Dell:U2723QE:A", "serial:Dell:U2723QE:B")
    a.output.port = "DP-2"
    assert get_monitor_ids([b, a]) == ("serial:Dell:U2723QE:B", "serial:Dell:U2723QE:A")


def test_monitor_ids_disambiguate_duplicate_serials_with_ports():
    a = output_screen("DP-1", "Dell", "U2723QE", "duplicate")
    b = output_screen("DP-2", "Dell", "U2723QE", "duplicate")
    ids = get_monitor_ids([a, b])
    assert ids == (
        "serial:Dell:U2723QE:duplicate|port:DP-1",
        "serial:Dell:U2723QE:duplicate|port:DP-2",
    )
    assert get_monitor_ids([b, a]) == ids[::-1]


def test_monitor_ids_disambiguate_indistinguishable_metadata_with_indices():
    screen = output_screen("DP-1", "Dell", "U2723QE", "duplicate")
    ids = get_monitor_ids([screen, screen])
    assert len(set(ids)) == 2
    assert ids[0].endswith("|screen:0")
    assert ids[1].endswith("|screen:1")


def test_monitor_ids_fall_back_to_connector_then_index():
    assert get_monitor_ids(
        [output_screen("eDP-1"), output_screen(), output_screen(make="Dell", model="unknown")]
    ) == ("port:eDP-1", "screen:1", "screen:2")


def test_monitor_ids_escape_components():
    assert get_monitor_ids([output_screen(make="a:b", model="c|d", serial="e/f")]) == (
        "serial:a%3Ab:c%7Cd:e%2Ff",
    )


def test_initial_assignments_start_each_monitors_preferences():
    policy = ScreenGroupPreferences()
    assert policy(context((("A", "3"), ("B", "2"))), None) == {
        "A": "3",
        "B": "2",
    }
    assert policy.priority == ["A", "B"]
    assert policy.preferences == {"A": ["3", "1", "2"], "B": ["2", "1", "3"]}


def test_explicit_preferences_take_precedence_and_incomplete_lists_are_extended():
    configured = {"A": ["3", "3"], "B": ["1"]}
    policy = ScreenGroupPreferences(configured)
    assert policy(context(), None) == {"A": "3", "B": "1"}
    assert policy.preferences == {"A": ["3", "1", "2"], "B": ["1", "2", "3"]}
    assert configured == {"A": ["3", "3"], "B": ["1"]}


def test_displaced_monitor_restores_favorite_after_group_is_released():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    assert policy(context(), select("B", "1")) == {"B": "1", "A": "2"}
    assert policy.preferences["A"] == ["1", "2", "3"]
    assert policy(context((("A", "2"), ("B", "1"))), select("B", "3")) == {
        "B": "3",
        "A": "1",
    }


def test_latest_request_promotes_monitor_and_group():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    policy(context(), select("B", "1"))
    assert policy(context((("A", "2"), ("B", "1"))), select("A", "1")) == {
        "A": "1",
        "B": "2",
    }
    assert policy.priority == ["A", "B"]
    assert policy.preferences["B"][0] == "1"


def test_reselection_promotes_monitor_even_when_assignment_does_not_change():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    assert policy(context(), select("B", "2")) == {"B": "2", "A": "1"}
    assert policy.priority == ["B", "A"]
    assert policy.preferences["B"] == ["2", "1", "3"]
    assert policy(context(), select("A", "1")) == {"A": "1", "B": "2"}
    assert policy.priority == ["A", "B"]


def test_passive_displacement_does_not_change_preferences_or_priority():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    # A snapshot can change because of native setup or displacement. Without a
    # request, neither displayed group is treated as a new preference.
    assert policy(context((("A", "2"), ("B", "1"))), None) == {"A": "1", "B": "2"}
    assert policy.priority == ["A", "B"]
    assert policy.preferences == {"A": ["1", "2", "3"], "B": ["2", "1", "3"]}


def test_reconciliation_preserves_request_history():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    policy(context(), select("B", "1"))
    preferences = {monitor_id: groups.copy() for monitor_id, groups in policy.preferences.items()}
    assert policy(context((("A", "2"), ("B", "1"))), None) == {
        "B": "1",
        "A": "2",
    }
    assert policy.priority == ["B", "A"]
    assert policy.preferences == preferences


def test_reconnect_and_monitor_order_changes_preserve_preferences_and_priority():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    policy(context(), select("B", "1"))
    assert policy(context((("A", "2"),)), None) == {"A": "1"}
    assert policy(context((("B", "2"), ("A", "1"))), None) == {"B": "1", "A": "2"}
    assert policy.priority == ["B", "A"]


def test_new_monitor_is_appended_after_remembered_priority():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    assert policy(
        context((("C", "1"), ("B", "2"), ("A", "1"))),
        None,
    ) == {"A": "1", "B": "2", "C": "3"}
    assert policy.priority == ["A", "B", "C"]


def test_removed_groups_are_skipped_and_new_groups_become_available():
    policy = ScreenGroupPreferences()
    policy(context(), None)
    policy(context(), select("B", "1"))
    changed = context((("A", "2"), ("B", "1")), groups=("2", "4"))
    assert policy(changed, None) == {"B": "2", "A": "4"}
    assert policy.priority == ["B", "A"]
    assert policy.preferences["A"] == ["1", "2", "3", "4"]


@pytest.mark.parametrize("selection", [select("unknown", "1"), select("A", "unknown")])
def test_invalid_requests_are_rejected_without_changing_history(selection):
    policy = ScreenGroupPreferences()
    policy(context(), None)
    with pytest.raises(ValueError, match="connected monitor and eligible group"):
        policy(context(groups=("1", "2", "3", "4")), selection)
    assert policy.priority == ["A", "B"]
    assert policy.preferences == {"A": ["1", "2", "3"], "B": ["2", "1", "3"]}


def test_too_few_groups_are_rejected():
    with pytest.raises(ValueError, match="at least one group per monitor"):
        ScreenGroupPreferences()(context(groups=("1",)), None)


def test_no_monitors_need_no_assignments():
    assert ScreenGroupPreferences()(context(()), None) == {}


def test_default_policy_selecting_hidden_group_changes_only_requesting_monitor():
    snapshot = context((("A", "1"), ("B", "2"), ("C", "3")), groups=("1", "2", "3", "4"))
    assert swap_screen_groups(snapshot, select("B", "4")) == {
        "A": "1",
        "B": "4",
        "C": "3",
    }


def test_default_policy_selecting_visible_group_swaps_requester_with_holder():
    snapshot = context((("A", "1"), ("B", "2"), ("C", "3")))
    assert swap_screen_groups(snapshot, select("B", "1")) == {
        "A": "2",
        "B": "1",
        "C": "3",
    }


def test_default_policy_reselecting_current_group_keeps_assignments():
    assert swap_screen_groups(context(), select("B", "2")) == {
        "A": "1",
        "B": "2",
    }


def test_default_policy_reconciliation_keeps_assignments():
    assert swap_screen_groups(context(), None) == {"A": "1", "B": "2"}


@pytest.mark.parametrize(
    "selection",
    [select("unknown", "1"), select("A", "unknown")],
)
def test_default_policy_invalid_requests_are_rejected(selection):
    with pytest.raises(ValueError):
        swap_screen_groups(context(), selection)


def test_default_policy_no_monitors_need_no_assignments():
    assert swap_screen_groups(context(()), None) == {}


def test_default_policy_assigns_groups_to_monitors_without_one():
    snapshot = context((("A", None), ("B", None)), groups=("1", "2", "3"))
    assert swap_screen_groups(snapshot, None) == {"A": "1", "B": "2"}


def test_default_policy_repairs_missing_groups_with_compatible_affinities():
    snapshot = context(
        (("A", None), ("B", None)),
        group_affinities=(("1", 0), ("2", 0), ("3", 1)),
    )
    assert swap_screen_groups(snapshot, None) == {"A": "1", "B": "3"}


def test_default_policy_affinities_do_not_restrict_existing_or_requested_assignments():
    snapshot = context(group_affinities=(("1", 1), ("2", 0), ("3", 0)))
    assert swap_screen_groups(snapshot, None) == {"A": "1", "B": "2"}
    assert swap_screen_groups(snapshot, select("B", "3")) == {"A": "1", "B": "3"}


def test_default_policy_repairs_invalid_and_duplicate_snapshot_groups():
    snapshot = context((("A", "gone"), ("B", "1"), ("C", "1")), groups=("1", "2", "3"))
    assert swap_screen_groups(snapshot, None) == {"A": "2", "B": "1", "C": "3"}


def test_default_policy_request_from_a_monitor_without_a_group():
    snapshot = context((("A", None), ("B", "2")), groups=("1", "2", "3"))
    assert swap_screen_groups(snapshot, select("A", "2")) == {"A": "2", "B": "1"}


def test_default_policy_rejects_snapshots_with_too_few_groups():
    with pytest.raises(ValueError, match="at least one group per monitor"):
        swap_screen_groups(context((("A", None), ("B", None)), groups=("1",)), None)


def test_preferences_assign_monitors_without_a_group_in_priority_order():
    policy = ScreenGroupPreferences()
    snapshot = context((("A", None), ("B", "2")), groups=("1", "2", "3"))
    assert policy(snapshot, None) == {"A": "1", "B": "2"}
    assert policy.preferences == {"A": ["1", "2", "3"], "B": ["2", "1", "3"]}
