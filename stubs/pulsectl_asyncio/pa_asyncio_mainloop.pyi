import asyncio
import ctypes as c

from _typeshed import Incomplete
from pulsectl._pulsectl import PA_MAINLOOP_API

class pa_mainloop_api(PA_MAINLOOP_API): ...

time_t_size: Incomplete
time_t = c.c_longlong

class timeval(c.Structure):
    def to_float(self) -> float: ...

PA_IO_EVENT_NULL: int
PA_IO_EVENT_INPUT: int
PA_IO_EVENT_OUTPUT: int
PA_IO_EVENT_HANGUP: int
PA_IO_EVENT_ERROR: int
pa_defer_event_p = c.c_void_p
pa_defer_event_cb_t: Incomplete
pa_defer_event_destroy_cb_t: Incomplete
pa_io_event_p = c.c_void_p
pa_io_event_flags = c.c_int
pa_io_event_cb_t: Incomplete
pa_io_event_destroy_cb_t: Incomplete
pa_time_event_p = c.c_void_p
pa_time_event_cb_t: Incomplete
pa_time_event_destroy_cb_t: Incomplete
pa_io_new_t: Incomplete
pa_io_enable_t: Incomplete
pa_io_set_destroy_t: Incomplete
pa_io_free_t: Incomplete
pa_time_new_t: Incomplete
pa_time_restart_t: Incomplete
pa_time_set_destroy_t: Incomplete
pa_time_free_t: Incomplete
pa_defer_new_t: Incomplete
pa_defer_enable_t: Incomplete
pa_defer_free_t: Incomplete
pa_defer_set_destroy_t: Incomplete
pa_quit_t: Incomplete

class PythonMainLoop:
    loop: Incomplete
    io_events: Incomplete
    defer_events: Incomplete
    time_events: Incomplete
    io_reader_events: Incomplete
    io_writer_events: Incomplete
    api_pointer: Incomplete
    retval: Incomplete
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None: ...
    def register_unregister_io_event(
        self, event: PythonIOEvent, reader: bool, writer: bool
    ) -> None: ...
    def stop(self, retval: int) -> None: ...

class PythonIOEvent:
    python_main_loop: Incomplete
    fd: Incomplete
    callback: Incomplete
    userdata: Incomplete
    on_destroy_callback: Incomplete
    writer: bool
    reader: bool
    self_pointer: Incomplete
    def __init__(
        self,
        python_main_loop: PythonMainLoop,
        fd: int,
        callback: pa_io_event_cb_t,
        userdata: c.c_void_p,
    ) -> None: ...
    def read(self) -> None: ...
    def write(self) -> None: ...
    def free(self) -> None: ...
    def set_destroy(self, callback: pa_io_event_destroy_cb_t) -> None: ...

class PythonTimeEvent:
    python_main_loop: Incomplete
    callback: Incomplete
    userdata: Incomplete
    on_destroy_callback: Incomplete
    handle: Incomplete
    self_pointer: Incomplete
    def __init__(
        self, python_main_loop: PythonMainLoop, callback: pa_time_event_cb_t, userdata: c.c_void_p
    ) -> None: ...
    def restart(self, ts: timeval) -> None: ...
    def free(self) -> None: ...
    def set_destroy(self, callback: pa_io_event_destroy_cb_t) -> None: ...

class PythonDeferEvent:
    python_main_loop: Incomplete
    callback: Incomplete
    userdata: Incomplete
    on_destroy_callback: Incomplete
    enabled: bool
    self_pointer: Incomplete
    handle: Incomplete
    def __init__(
        self,
        python_main_loop: PythonMainLoop,
        callback: pa_defer_event_cb_t,
        userdata: c.c_void_p,
    ) -> None: ...
    def call(self) -> None: ...
    def enable(self, enable: bool) -> None: ...
    def free(self) -> None: ...
    def set_destroy(self, callback: pa_io_event_destroy_cb_t) -> None: ...

def aio_io_new(
    main_loop: None, fd: int, flags: int, cb: pa_io_event_cb_t, userdata: c.c_void_p
) -> int: ...
def aio_io_enable(e: pa_io_event_p, flags: int) -> None: ...
def aio_io_set_destroy(e: pa_io_event_p, cb: pa_io_event_destroy_cb_t) -> None: ...
def aio_io_free(e: pa_io_event_p) -> None: ...
def aio_time_new(
    main_loop: None, ts: None, cb: pa_io_event_cb_t, userdata: c.c_void_p
) -> int: ...
def aio_time_restart(e: pa_time_event_p, ts: None) -> None: ...
def aio_time_set_destroy(e: pa_time_event_p, cb: pa_time_event_destroy_cb_t) -> None: ...
def aio_time_free(e: pa_io_event_p) -> None: ...
def aio_defer_new(main_loop: None, cb: pa_defer_event_cb_t, userdata: c.c_void_p) -> int: ...
def aio_defer_enable(e: pa_defer_event_p, enable: bool) -> None: ...
def aio_defer_set_destroy(e: pa_defer_event_p, cb: pa_defer_event_destroy_cb_t) -> None: ...
def aio_defer_free(e: pa_io_event_p) -> None: ...
def aio_quit(main_loop: None, retval: int) -> None: ...
