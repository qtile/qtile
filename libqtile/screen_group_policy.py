"""Policies for assigning groups to monitors."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from libqtile.config import Screen


@dataclass(frozen=True)
class ScreenGroupMonitor:
    """Immutable monitor identity, metadata, screen index, and displayed group.

    ``group`` is ``None`` while the monitor has no group attached, for example
    before the initial assignment or after its group was removed.
    """

    id: str
    index: int
    port: str | None
    make: str | None
    model: str | None
    serial: str | None
    group: str | None


@dataclass(frozen=True)
class ScreenGroupContext:
    """Immutable monitor snapshot, eligible groups, and configured screen affinities."""

    monitors: tuple[ScreenGroupMonitor, ...]
    groups: tuple[str, ...]
    group_affinities: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class ScreenGroupRequest:
    """An immutable request to select a group on a monitor."""

    monitor_id: str
    group_name: str


def swap_screen_groups(
    context: ScreenGroupContext, request: ScreenGroupRequest | None
) -> dict[str, str]:
    """Return assignments selecting the requested group, swapping if already visible.

    With ``request=None``, return the snapshot's assignments. Monitors without a
    group, or displaying a group that is no longer eligible or duplicated, are
    repaired with unused groups, preferring compatible screen affinities.
    """
    snapshot = {monitor.id: monitor.group for monitor in context.monitors}
    eligible = set(context.groups)
    used: set[str] = set()
    for monitor in context.monitors:
        group = snapshot[monitor.id]
        if group is None or group not in eligible or group in used:
            snapshot[monitor.id] = None
        else:
            used.add(group)
    available = [group for group in context.groups if group not in used]
    affinities = dict(context.group_affinities)
    for monitor in context.monitors:
        if snapshot[monitor.id] is None:
            if not available:
                raise ValueError("A screen group policy needs at least one group per monitor.")
            group = next(
                (group for group in available if affinities.get(group) in (None, monitor.index)),
                available[0],
            )
            snapshot[monitor.id] = group
            available.remove(group)
    assignments = {
        monitor_id: group for monitor_id, group in snapshot.items() if group is not None
    }
    if request is None:
        return assignments
    if request.monitor_id not in assignments or request.group_name not in context.groups:
        raise ValueError("A request must name a connected monitor and eligible group.")

    previous = assignments[request.monitor_id]
    for monitor_id, group_name in assignments.items():
        if group_name == request.group_name:
            assignments[monitor_id] = previous
            break
    assignments[request.monitor_id] = request.group_name
    return assignments


def get_monitor_ids(screens: Sequence[Screen]) -> tuple[str, ...]:
    """Return unique monitor IDs in screen order.

    Prefer serial metadata, then connector, then screen index. Resolve duplicate
    identities with connector and index suffixes.
    """

    def escape(value: str | None) -> str:
        return quote(value or "", safe="")

    identities = []
    for index, screen in enumerate(screens):
        output = screen.output
        if output.serial:
            identity = (
                f"serial:{escape(output.make)}:{escape(output.model)}:{escape(output.serial)}"
            )
        elif output.port:
            identity = f"port:{escape(output.port)}"
        else:
            identity = f"screen:{index}"
        identities.append(identity)

    counts = Counter(identities)
    identities = [
        f"{identity}|port:{escape(screen.output.port)}"
        if counts[identity] > 1 and screen.output.port
        else identity
        for screen, identity in zip(screens, identities)
    ]
    counts = Counter(identities)
    return tuple(
        f"{identity}|screen:{index}" if counts[identity] > 1 else identity
        for index, identity in enumerate(identities)
    )


class ScreenGroupPreferences:
    """Assign each monitor its first available group, in monitor priority order.

    A request moves its monitor and group to the front of their respective
    orderings. ``request=None`` recomputes assignments without promotion.

    ``preferences`` maps monitor IDs to ordered group names. Unlisted groups
    follow in configuration order; unlisted monitors start with their displayed
    group. New monitors join the end of the priority order. Preferences and priority
    persist across disconnections for this object's lifetime.
    """

    def __init__(self, preferences: Mapping[str, Sequence[str]] | None = None) -> None:
        self.preferences: dict[str, list[str]] = {
            monitor_id: list(dict.fromkeys(groups))
            for monitor_id, groups in (preferences or {}).items()
        }
        self.priority: list[str] = []

    def __call__(
        self, context: ScreenGroupContext, request: ScreenGroupRequest | None
    ) -> dict[str, str]:
        monitors = {monitor.id: monitor for monitor in context.monitors}
        available = set(context.groups)
        if len(available) < len(monitors):
            raise ValueError("A screen group policy needs at least one group per monitor.")
        if request is not None:
            if request.monitor_id not in monitors or request.group_name not in available:
                raise ValueError("A request must name a connected monitor and eligible group.")

        unassigned = set()
        for monitor in context.monitors:
            if monitor.id not in self.priority:
                self.priority.append(monitor.id)
            if monitor.id not in self.preferences:
                self.preferences[monitor.id] = [monitor.group] if monitor.group else []
                if monitor.group is None:
                    unassigned.add(monitor.id)
            preferences = self.preferences[monitor.id]
            preferences.extend(group for group in context.groups if group not in preferences)

        if request is not None:
            self.priority.remove(request.monitor_id)
            self.priority.insert(0, request.monitor_id)
            preferences = self.preferences[request.monitor_id]
            if request.group_name in preferences:
                preferences.remove(request.group_name)
            preferences.insert(0, request.group_name)

        priority = [monitor_id for monitor_id in self.priority if monitor_id in monitors]
        assignments = {}
        for monitor_id in priority:
            group = next(group for group in self.preferences[monitor_id] if group in available)
            assignments[monitor_id] = group
            available.remove(group)

        for monitor_id in unassigned:
            # A monitor that has never displayed a group favors its first assignment.
            preferences = self.preferences[monitor_id]
            preferences.remove(assignments[monitor_id])
            preferences.insert(0, assignments[monitor_id])

        return assignments
