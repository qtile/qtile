import time
from ctypes import *

from _typeshed import Incomplete

force_str: Incomplete
force_bytes: Incomplete

class c_str_p_type:
    c_type = c_char_p
    def __call__(self, val): ...
    def from_param(self, val): ...

unicode: Incomplete
c_str_p: Incomplete
mono_time = time.monotonic
c_str_p = c_char_p
PA_INVALID: Incomplete
PA_VOLUME_NORM: int
PA_VOLUME_MAX: Incomplete
PA_VOLUME_INVALID: Incomplete
pa_sw_volume_from_dB: Incomplete
PA_VOLUME_UI_MAX: int
PA_CHANNELS_MAX: int
PA_USEC_T = c_uint64
PA_CONTEXT_NOAUTOSPAWN: int
PA_CONTEXT_NOFAIL: int
PA_CONTEXT_UNCONNECTED: int
PA_CONTEXT_CONNECTING: int
PA_CONTEXT_AUTHORIZING: int
PA_CONTEXT_SETTING_NAME: int
PA_CONTEXT_READY: int
PA_CONTEXT_FAILED: int
PA_CONTEXT_TERMINATED: int
PA_SUBSCRIPTION_MASK_NULL: int
PA_SUBSCRIPTION_MASK_SINK: int
PA_SUBSCRIPTION_MASK_SOURCE: int
PA_SUBSCRIPTION_MASK_SINK_INPUT: int
PA_SUBSCRIPTION_MASK_SOURCE_OUTPUT: int
PA_SUBSCRIPTION_MASK_MODULE: int
PA_SUBSCRIPTION_MASK_CLIENT: int
PA_SUBSCRIPTION_MASK_SAMPLE_CACHE: int
PA_SUBSCRIPTION_MASK_SERVER: int
PA_SUBSCRIPTION_MASK_AUTOLOAD: int
PA_SUBSCRIPTION_MASK_CARD: int
PA_SUBSCRIPTION_MASK_ALL: int
PA_SUBSCRIPTION_EVENT_SINK: int
PA_SUBSCRIPTION_EVENT_SOURCE: int
PA_SUBSCRIPTION_EVENT_SINK_INPUT: int
PA_SUBSCRIPTION_EVENT_SOURCE_OUTPUT: int
PA_SUBSCRIPTION_EVENT_MODULE: int
PA_SUBSCRIPTION_EVENT_CLIENT: int
PA_SUBSCRIPTION_EVENT_SAMPLE_CACHE: int
PA_SUBSCRIPTION_EVENT_SERVER: int
PA_SUBSCRIPTION_EVENT_AUTOLOAD: int
PA_SUBSCRIPTION_EVENT_CARD: int
PA_SUBSCRIPTION_EVENT_FACILITY_MASK: int
PA_SUBSCRIPTION_EVENT_NEW: int
PA_SUBSCRIPTION_EVENT_CHANGE: int
PA_SUBSCRIPTION_EVENT_REMOVE: int
PA_SUBSCRIPTION_EVENT_TYPE_MASK: int
PA_SAMPLE_FLOAT32LE: int
PA_SAMPLE_FLOAT32BE: int
PA_SAMPLE_FLOAT32NE: Incomplete
PA_STREAM_DONT_MOVE: int
PA_STREAM_PEAK_DETECT: int
PA_STREAM_ADJUST_LATENCY: int
PA_STREAM_DONT_INHIBIT_AUTO_SUSPEND: int

def c_enum_map(**values): ...

k: Incomplete
PA_EVENT_TYPE_MAP: Incomplete
PA_EVENT_FACILITY_MAP: Incomplete
PA_EVENT_MASK_MAP: Incomplete
PA_UPDATE_MAP: Incomplete
PA_PORT_AVAILABLE_MAP: Incomplete
PA_DIRECTION_MAP: Incomplete
PA_OBJ_STATE_MAP: Incomplete

class PA_MAINLOOP(Structure): ...
class PA_STREAM(Structure): ...
class PA_MAINLOOP_API(Structure): ...
class PA_CONTEXT(Structure): ...
class PA_PROPLIST(Structure): ...
class PA_OPERATION(Structure): ...
class PA_SIGNAL_EVENT(Structure): ...
class PA_IO_EVENT(Structure): ...
class PA_SAMPLE_SPEC(Structure): ...
class PA_CHANNEL_MAP(Structure): ...
class PA_CVOLUME(Structure): ...
class PA_PORT_INFO(Structure): ...
class PA_SINK_INPUT_INFO(Structure): ...
class PA_SINK_INFO(Structure): ...
class PA_SOURCE_OUTPUT_INFO(Structure): ...
class PA_SOURCE_INFO(Structure): ...
class PA_CLIENT_INFO(Structure): ...
class PA_SERVER_INFO(Structure): ...
class PA_CARD_PROFILE_INFO(Structure): ...
class PA_CARD_PORT_INFO(Structure): ...
class PA_CARD_INFO(Structure): ...
class PA_MODULE_INFO(Structure): ...
class PA_EXT_STREAM_RESTORE_INFO(Structure): ...
class PA_BUFFER_ATTR(Structure): ...
class POLLFD(Structure): ...

PA_POLL_FUNC_T: Incomplete
PA_SIGNAL_CB_T: Incomplete
PA_STATE_CB_T: Incomplete
PA_CLIENT_INFO_CB_T: Incomplete
PA_SERVER_INFO_CB_T: Incomplete
PA_SINK_INPUT_INFO_CB_T: Incomplete
PA_SINK_INFO_CB_T: Incomplete
PA_SOURCE_OUTPUT_INFO_CB_T: Incomplete
PA_SOURCE_INFO_CB_T: Incomplete
PA_CONTEXT_DRAIN_CB_T: Incomplete
PA_CONTEXT_INDEX_CB_T: Incomplete
PA_CONTEXT_SUCCESS_CB_T: Incomplete
PA_EXT_STREAM_RESTORE_TEST_CB_T: Incomplete
PA_EXT_STREAM_RESTORE_READ_CB_T: Incomplete
PA_CARD_INFO_CB_T: Incomplete
PA_MODULE_INFO_CB_T: Incomplete
PA_SUBSCRIBE_CB_T: Incomplete
PA_STREAM_REQUEST_CB_T: Incomplete
PA_STREAM_NOTIFY_CB_T: Incomplete

class LibPulse:
    func_defs: Incomplete

    class CallError(Exception): ...
    funcs: Incomplete
    def __init__(self) -> None: ...
    def __getattr__(self, k): ...
    def return_value(self): ...

pa: Incomplete
