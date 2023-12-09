from collections import defaultdict as defaultdict

from _typeshed import Incomplete

long: Incomplete
unicode: Incomplete
print_err: Incomplete

def wrapper_with_sig_info(func, wrapper, index_arg: bool = ...): ...

range: Incomplete
map: Incomplete
is_str: Incomplete
is_str_native: Incomplete
is_num: Incomplete
is_list: Incomplete
is_dict: Incomplete

def assert_pulse_object(obj) -> None: ...

class FakeLock:
    def __enter__(self): ...
    def __exit__(self, *err) -> None: ...

class EnumValue:
    def __init__(self, t, value, c_value: Incomplete | None = ...) -> None: ...
    def __eq__(self, val): ...
    def __ne__(self, val): ...
    def __lt__(self, val): ...
    def __hash__(self): ...

class Enum:
    def __init__(self, name, values_or_map) -> None: ...
    def __getitem__(self, k, *default): ...
    def __contains__(self, k) -> bool: ...

PulseEventTypeEnum: Incomplete
PulseEventFacilityEnum: Incomplete
PulseEventMaskEnum: Incomplete
PulseStateEnum: Incomplete
PulseUpdateEnum: Incomplete
PulsePortAvailableEnum: Incomplete
PulseDirectionEnum: Incomplete

class PulseError(Exception): ...
class PulseOperationFailed(PulseError): ...
class PulseOperationInvalid(PulseOperationFailed): ...
class PulseIndexError(PulseError): ...
class PulseLoopStop(Exception): ...
class PulseDisconnected(Exception): ...

class PulseObject:
    c_struct_wrappers: Incomplete
    volume: Incomplete
    base_volume: Incomplete
    port_list: Incomplete
    port_active: Incomplete
    channel_list_raw: Incomplete
    state: Incomplete
    state_values: Incomplete
    corked: Incomplete
    def __init__(
        self, struct: Incomplete | None = ..., *field_data_list, **field_data_dict
    ) -> None: ...

class PulsePortInfo(PulseObject):
    c_struct_fields: str
    def __eq__(self, o): ...
    def __hash__(self): ...

class PulseClientInfo(PulseObject):
    c_struct_fields: str

class PulseServerInfo(PulseObject):
    c_struct_fields: str

class PulseModuleInfo(PulseObject):
    c_struct_fields: str

class PulseSinkInfo(PulseObject):
    c_struct_fields: str

class PulseSinkInputInfo(PulseObject):
    c_struct_fields: str

class PulseSourceInfo(PulseObject):
    c_struct_fields: str

class PulseSourceOutputInfo(PulseObject):
    c_struct_fields: str

class PulseCardProfileInfo(PulseObject):
    c_struct_fields: str

class PulseCardPortInfo(PulsePortInfo):
    c_struct_fields: str

class PulseCardInfo(PulseObject):
    c_struct_fields: str
    c_struct_wrappers: Incomplete
    profile_list: Incomplete
    profile_active: Incomplete
    def __init__(self, struct) -> None: ...

class PulseVolumeInfo(PulseObject):
    values: Incomplete
    def __init__(
        self, struct_or_values: Incomplete | None = ..., channels: Incomplete | None = ...
    ) -> None: ...
    @property
    def value_flat(self): ...
    @value_flat.setter
    def value_flat(self, v) -> None: ...
    def to_struct(self): ...

class PulseExtStreamRestoreInfo(PulseObject):
    c_struct_fields: str
    @classmethod
    def struct_from_value(
        cls,
        name,
        volume,
        channel_list: Incomplete | None = ...,
        mute: bool = ...,
        device: Incomplete | None = ...,
    ): ...
    def __init__(
        self,
        struct_or_name: Incomplete | None = ...,
        volume: Incomplete | None = ...,
        channel_list: Incomplete | None = ...,
        mute: bool = ...,
        device: Incomplete | None = ...,
    ) -> None: ...
    def to_struct(self): ...

class PulseEventInfo(PulseObject):
    def __init__(self, ev_t, facility, index) -> None: ...

class Pulse:
    name: Incomplete
    def __init__(
        self,
        client_name: Incomplete | None = ...,
        server: Incomplete | None = ...,
        connect: bool = ...,
        threading_lock: bool = ...,
    ) -> None: ...
    event_types: Incomplete
    event_facilities: Incomplete
    event_masks: Incomplete
    event_callback: Incomplete
    channel_list_enum: Incomplete
    def init(self) -> None: ...
    connected: bool
    def connect(
        self, autospawn: bool = ..., wait: bool = ..., timeout: Incomplete | None = ...
    ) -> None: ...
    def disconnect(self) -> None: ...
    def close(self) -> None: ...
    def __enter__(self): ...
    def __exit__(self, err_t, err, err_tb) -> None: ...
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
    def module_load(self, name, args: str = ...): ...
    module_unload: Incomplete
    def stream_restore_test(self): ...
    stream_restore_read: Incomplete
    stream_restore_list = stream_restore_read
    def stream_restore_write(
        obj_name_or_list, mode: str = ..., apply_immediately: bool = ..., **obj_kws
    ): ...
    def stream_restore_delete(obj_name_or_list): ...
    def default_set(self, obj) -> None: ...
    def mute(self, obj, mute: bool = ...) -> None: ...
    def port_set(self, obj, port) -> None: ...
    def card_profile_set(self, card, profile) -> None: ...
    def volume_set(self, obj, vol) -> None: ...
    def volume_set_all_chans(self, obj, vol) -> None: ...
    def volume_change_all_chans(self, obj, inc) -> None: ...
    def volume_get_all_chans(self, obj): ...
    def event_mask_set(self, *masks) -> None: ...
    def event_callback_set(self, func) -> None: ...
    def event_listen(
        self, timeout: Incomplete | None = ..., raise_on_disconnect: bool = ...
    ) -> None: ...
    def event_listen_stop(self) -> None: ...
    def set_poll_func(self, func, func_err_handler: Incomplete | None = ...) -> None: ...
    def get_peak_sample(self, source, timeout, stream_idx: Incomplete | None = ...): ...
    def play_sample(
        self,
        name,
        sink: Incomplete | None = ...,
        volume: float = ...,
        proplist_str: Incomplete | None = ...,
    ) -> None: ...

def connect_to_cli(
    server: Incomplete | None = ...,
    as_file: bool = ...,
    socket_timeout: float = ...,
    attempts: int = ...,
    retry_delay: float = ...,
): ...
