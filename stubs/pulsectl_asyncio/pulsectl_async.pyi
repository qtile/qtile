import asyncio
from typing import AsyncIterator, Optional

from _typeshed import Incomplete
from pulsectl.pulsectl import PulseEventInfo

from .pa_asyncio_mainloop import PythonMainLoop as PythonMainLoop

class _pulse_op_cb:
    raw: Incomplete
    future: Incomplete
    async_pulse: Incomplete
    def __init__(self, async_pulse: PulseAsync, raw: bool = ...) -> None: ...
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...

class PulseAsync:
    name: Incomplete
    server: Incomplete
    def __init__(
        self,
        client_name: Incomplete | None = ...,
        server: Incomplete | None = ...,
        loop: Optional[asyncio.AbstractEventLoop] = ...,
    ) -> None: ...
    event_types: Incomplete
    event_facilities: Incomplete
    event_masks: Incomplete
    event_callback: Incomplete
    waiting_futures: Incomplete
    channel_list_enum: Incomplete
    def init(self, loop: Optional[asyncio.AbstractEventLoop]): ...
    async def connect(
        self, autospawn: bool = ..., wait: bool = ..., timeout: Incomplete | None = ...
    ) -> None: ...
    @property
    def connected(self): ...
    def disconnect(self) -> None: ...
    def close(self) -> None: ...
    def __enter__(self): ...
    def __exit__(self, err_t, err, err_tb) -> None: ...
    async def __aenter__(self): ...
    async def __aexit__(self, err_t, err, err_tb) -> None: ...
    get_sink_by_name: Incomplete
    get_source_by_name: Incomplete
    get_card_by_name: Incomplete
    sink_input_list: Incomplete
    sink_input_info: Incomplete
    source_output_list: Incomplete
    source_output_info: Incomplete
    sink_list: Incomplete
    sink_info: Incomplete
    source_list: Incomplete
    source_info: Incomplete
    card_list: Incomplete
    card_info: Incomplete
    client_list: Incomplete
    client_info: Incomplete
    server_info: Incomplete
    module_info: Incomplete
    module_list: Incomplete
    card_profile_set_by_index: Incomplete
    sink_default_set: Incomplete
    source_default_set: Incomplete
    sink_input_mute: Incomplete
    sink_input_move: Incomplete
    sink_mute: Incomplete
    sink_input_volume_set: Incomplete
    sink_volume_set: Incomplete
    sink_suspend: Incomplete
    sink_port_set: Incomplete
    source_output_mute: Incomplete
    source_output_move: Incomplete
    source_mute: Incomplete
    source_output_volume_set: Incomplete
    source_volume_set: Incomplete
    source_suspend: Incomplete
    source_port_set: Incomplete
    async def module_load(self, name, args: str = ...): ...
    module_unload: Incomplete
    async def stream_restore_test(self): ...
    stream_restore_read: Incomplete
    stream_restore_list = stream_restore_read
    def stream_restore_write(
        obj_name_or_list, mode: str = ..., apply_immediately: bool = ..., **obj_kws
    ): ...
    def stream_restore_delete(obj_name_or_list): ...
    async def default_set(self, obj) -> None: ...
    async def mute(self, obj, mute: bool = ...) -> None: ...
    async def port_set(self, obj, port) -> None: ...
    async def card_profile_set(self, card, profile) -> None: ...
    async def volume_set(self, obj, vol) -> None: ...
    async def volume_set_all_chans(self, obj, vol) -> None: ...
    async def volume_change_all_chans(self, obj, inc) -> None: ...
    async def volume_get_all_chans(self, obj): ...
    async def subscribe_events(self, *masks) -> AsyncIterator[PulseEventInfo]: ...
    async def get_peak_sample(self, source, timeout, stream_idx: Incomplete | None = ...): ...
    async def subscribe_peak_sample(
        self,
        source,
        rate: int = ...,
        stream_idx: Incomplete | None = ...,
        allow_suspend: bool = ...,
    ) -> AsyncIterator[float]: ...
    async def play_sample(
        self,
        name,
        sink: Incomplete | None = ...,
        volume: float = ...,
        proplist_str: Incomplete | None = ...,
    ) -> None: ...
