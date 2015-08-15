# generation commands
# h2xml.py -I $PWD -c -o pa.xml pulse/mainloop-api.h pulse/sample.h pulse/def.h pulse/operation.h pulse/context.h pulse/channelmap.h pulse/volume.h pulse/stream.h pulse/introspect.h pulse/subscribe.h pulse/scache.h pulse/version.h pulse/error.h pulse/xmalloc.h pulse/utf8.h pulse/thread-mainloop.h pulse/mainloop.h pulse/mainloop-signal.h pulse/util.h pulse/timeval.h
# xml2py.py -k efstd -o lib_pulseaudio.py -l 'pulse' -r '(pa|PA)_.+' pa.xml

from ctypes import *
import shutil
import subprocess
from libqtile.widget import base 

_libraries = {}
_libraries['libpulse.so.0'] = CDLL('libpulse.so.0')
STRING = c_char_p
pa_volume_t = c_uint32
pa_channel_position_t = c_int
pa_usec_t = c_uint64
pa_channel_position_mask_t = c_uint64

PA_CONTEXT_READY = 4
PA_OK = 0
PA_OPERATION_CANCELLED = 2
PA_OPERATION_DONE = 1
PA_OPERATION_RUNNING = 0
PA_SUBSCRIPTION_EVENT_CHANGE = 16
PA_SUBSCRIPTION_EVENT_FACILITY_MASK = 15
PA_SUBSCRIPTION_EVENT_SERVER = 7
PA_SUBSCRIPTION_MASK_SINK = 1
PA_SUBSCRIPTION_MASK_SERVER = 0x80


class pa_sink_port_info(Structure):
    pass


class pa_format_info(Structure):
    pass


class pa_context(Structure):
    pass


pa_context._fields_ = [
]
pa_context_notify_cb_t = CFUNCTYPE(None, POINTER(pa_context), c_void_p)
pa_context_success_cb_t = CFUNCTYPE(None, POINTER(pa_context), c_int, c_void_p)


class pa_proplist(Structure):
    pass


pa_context_event_cb_t = CFUNCTYPE(
    None, POINTER(pa_context), STRING, POINTER(pa_proplist), c_void_p)


class pa_mainloop_api(Structure):
    pass


pa_context_new = _libraries['libpulse.so.0'].pa_context_new
pa_context_new.restype = POINTER(pa_context)
pa_context_new.argtypes = [POINTER(pa_mainloop_api), STRING]
pa_context_new_with_proplist = _libraries[
    'libpulse.so.0'].pa_context_new_with_proplist
pa_context_new_with_proplist.restype = POINTER(pa_context)
pa_context_new_with_proplist.argtypes = [
    POINTER(pa_mainloop_api), STRING, POINTER(pa_proplist)]
pa_context_unref = _libraries['libpulse.so.0'].pa_context_unref
pa_context_unref.restype = None
pa_context_unref.argtypes = [POINTER(pa_context)]
pa_context_ref = _libraries['libpulse.so.0'].pa_context_ref
pa_context_ref.restype = POINTER(pa_context)
pa_context_ref.argtypes = [POINTER(pa_context)]
pa_context_set_state_callback = _libraries[
    'libpulse.so.0'].pa_context_set_state_callback
pa_context_set_state_callback.restype = None
pa_context_set_state_callback.argtypes = [
    POINTER(pa_context), pa_context_notify_cb_t, c_void_p]


# values for enumeration 'pa_context_state'
pa_context_state = c_int  # enum
pa_context_state_t = pa_context_state
pa_context_get_state = _libraries['libpulse.so.0'].pa_context_get_state
pa_context_get_state.restype = pa_context_state_t
pa_context_get_state.argtypes = [POINTER(pa_context)]

# values for enumeration 'pa_context_flags'
pa_context_flags = c_int  # enum
pa_context_flags_t = pa_context_flags


class pa_spawn_api(Structure):
    _fields_ = [
        ('prefork', CFUNCTYPE(None)),
        ('postfork', CFUNCTYPE(None)),
        ('atfork', CFUNCTYPE(None)),
    ]


pa_context_connect = _libraries['libpulse.so.0'].pa_context_connect
pa_context_connect.restype = c_int
pa_context_connect.argtypes = [
    POINTER(pa_context), STRING, pa_context_flags_t, POINTER(pa_spawn_api)]
pa_context_disconnect = _libraries['libpulse.so.0'].pa_context_disconnect
pa_context_disconnect.restype = None
pa_context_disconnect.argtypes = [POINTER(pa_context)]


class pa_operation(Structure):
    pass


class pa_sample_spec(Structure):
    _fields_ = [
        ('format', c_int),
        ('rate', c_uint32),
        ('channels', c_uint8),
    ]

# values for enumeration 'pa_subscription_mask'
pa_subscription_mask = c_int  # enum
pa_subscription_mask_t = pa_subscription_mask

# values for enumeration 'pa_subscription_event_type'
pa_subscription_event_type = c_int  # enum
pa_subscription_event_type_t = pa_subscription_event_type

pa_context_subscribe_cb_t = CFUNCTYPE(
    None, POINTER(pa_context), pa_subscription_event_type_t, c_uint32, c_void_p)
pa_context_subscribe = _libraries['libpulse.so.0'].pa_context_subscribe
pa_context_subscribe.restype = POINTER(pa_operation)
pa_context_subscribe.argtypes = [
    POINTER(pa_context), pa_subscription_mask_t, pa_context_success_cb_t, c_void_p]
pa_context_set_subscribe_callback = _libraries[
    'libpulse.so.0'].pa_context_set_subscribe_callback
pa_context_set_subscribe_callback.restype = None
pa_context_set_subscribe_callback.argtypes = [
    POINTER(pa_context), pa_context_subscribe_cb_t, c_void_p]

# values for enumeration 'pa_sink_flags'
pa_sink_flags = c_int  # enum
pa_sink_flags_t = pa_sink_flags

# values for enumeration 'pa_sink_state'
pa_sink_state = c_int  # enum
pa_sink_state_t = pa_sink_state

pa_free_cb_t = CFUNCTYPE(None, c_void_p)
pa_strerror = _libraries['libpulse.so.0'].pa_strerror
pa_strerror.restype = STRING
pa_strerror.argtypes = [c_int]


class pa_sink_info(Structure):
    pass


class pa_cvolume(Structure):
    _fields_ = [
        ('channels', c_uint8),
        ('values', pa_volume_t * 32),
    ]


class pa_channel_map(Structure):
    _fields_ = [
        ('channels', c_uint8),
        ('map', pa_channel_position_t * 32),
    ]


pa_sink_info._fields_ = [
    ('name', STRING),
    ('index', c_uint32),
    ('description', STRING),
    ('sample_spec', pa_sample_spec),
    ('channel_map', pa_channel_map),
    ('owner_module', c_uint32),
    ('volume', pa_cvolume),
    ('mute', c_int),
    ('monitor_source', c_uint32),
    ('monitor_source_name', STRING),
    ('latency', pa_usec_t),
    ('driver', STRING),
    ('flags', pa_sink_flags_t),
    ('proplist', POINTER(pa_proplist)),
    ('configured_latency', pa_usec_t),
    ('base_volume', pa_volume_t),
    ('state', pa_sink_state_t),
    ('n_volume_steps', c_uint32),
    ('card', c_uint32),
    ('n_ports', c_uint32),
    ('ports', POINTER(POINTER(pa_sink_port_info))),
    ('active_port', POINTER(pa_sink_port_info)),
    ('n_formats', c_uint8),
    ('formats', POINTER(POINTER(pa_format_info))),
]
pa_sink_info_cb_t = CFUNCTYPE(
    None, POINTER(pa_context), POINTER(pa_sink_info), c_int, c_void_p)
pa_context_get_sink_info_by_name = _libraries[
    'libpulse.so.0'].pa_context_get_sink_info_by_name
pa_context_get_sink_info_by_name.restype = POINTER(pa_operation)
pa_context_get_sink_info_by_name.argtypes = [
    POINTER(pa_context), STRING, pa_sink_info_cb_t, c_void_p]
pa_context_get_sink_info_by_index = _libraries[
    'libpulse.so.0'].pa_context_get_sink_info_by_index
pa_context_get_sink_info_by_index.restype = POINTER(pa_operation)
pa_context_get_sink_info_by_index.argtypes = [
    POINTER(pa_context), c_uint32, pa_sink_info_cb_t, c_void_p]
pa_context_get_sink_info_list = _libraries[
    'libpulse.so.0'].pa_context_get_sink_info_list
pa_context_get_sink_info_list.restype = POINTER(pa_operation)
pa_context_get_sink_info_list.argtypes = [
    POINTER(pa_context), pa_sink_info_cb_t, c_void_p]


class pa_server_info(Structure):
    pass


pa_server_info._fields_ = [
    ('user_name', STRING),
    ('host_name', STRING),
    ('server_version', STRING),
    ('server_name', STRING),
    ('sample_spec', pa_sample_spec),
    ('default_sink_name', STRING),
    ('default_source_name', STRING),
    ('cookie', c_uint32),
    ('channel_map', pa_channel_map),
]
pa_server_info_cb_t = CFUNCTYPE(
    None, POINTER(pa_context), POINTER(pa_server_info), c_void_p)
pa_context_get_server_info = _libraries[
    'libpulse.so.0'].pa_context_get_server_info
pa_context_get_server_info.restype = POINTER(pa_operation)
pa_context_get_server_info.argtypes = [
    POINTER(pa_context), pa_server_info_cb_t, c_void_p]


class pa_threaded_mainloop(Structure):
    pass


pa_threaded_mainloop._fields_ = [
]
pa_threaded_mainloop_new = _libraries['libpulse.so.0'].pa_threaded_mainloop_new
pa_threaded_mainloop_new.restype = POINTER(pa_threaded_mainloop)
pa_threaded_mainloop_new.argtypes = []
pa_threaded_mainloop_free = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_free
pa_threaded_mainloop_free.restype = None
pa_threaded_mainloop_free.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_start = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_start
pa_threaded_mainloop_start.restype = c_int
pa_threaded_mainloop_start.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_stop = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_stop
pa_threaded_mainloop_stop.restype = None
pa_threaded_mainloop_stop.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_lock = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_lock
pa_threaded_mainloop_lock.restype = None
pa_threaded_mainloop_lock.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_unlock = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_unlock
pa_threaded_mainloop_unlock.restype = None
pa_threaded_mainloop_unlock.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_wait = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_wait
pa_threaded_mainloop_wait.restype = None
pa_threaded_mainloop_wait.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_signal = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_signal
pa_threaded_mainloop_signal.restype = None
pa_threaded_mainloop_signal.argtypes = [POINTER(pa_threaded_mainloop), c_int]
pa_threaded_mainloop_accept = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_accept
pa_threaded_mainloop_accept.restype = None
pa_threaded_mainloop_accept.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_get_retval = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_get_retval
pa_threaded_mainloop_get_retval.restype = c_int
pa_threaded_mainloop_get_retval.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_get_api = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_get_api
pa_threaded_mainloop_get_api.restype = POINTER(pa_mainloop_api)
pa_threaded_mainloop_get_api.argtypes = [POINTER(pa_threaded_mainloop)]
pa_threaded_mainloop_in_thread = _libraries[
    'libpulse.so.0'].pa_threaded_mainloop_in_thread
pa_threaded_mainloop_in_thread.restype = c_int
pa_threaded_mainloop_in_thread.argtypes = [POINTER(pa_threaded_mainloop)]

pa_sw_volume_to_dB = _libraries['libpulse.so.0'].pa_sw_volume_to_dB
pa_sw_volume_to_dB.restype = c_double
pa_sw_volume_to_dB.argtypes = [pa_volume_t]

pa_operation_unref = _libraries['libpulse.so.0'].pa_operation_unref
pa_operation_unref.restype = None
pa_operation_unref.argtypes = [POINTER(pa_operation)]



class PulseAudio(base.InLoopPollText):

    def __init__(self, *args, **kwargs):
        super(PulseAudio, self).__init__(*args, update_interval=1, **kwargs)
        """Creates context, when context is ready context_notify_cb is called"""
        # Wrap callback methods in appropriate ctypefunc instances so
        # that the Pulseaudio C API can call them
        self._context_notify_cb = pa_context_notify_cb_t(
            self.context_notify_cb)
        self._sink_info_cb = pa_sink_info_cb_t(self.sink_info_cb)
        self._update_cb = pa_context_subscribe_cb_t(self.update_cb)
        self._success_cb = pa_context_success_cb_t(self.success_cb)
        self._server_info_cb = pa_server_info_cb_t(self.server_info_cb)

        # Create the mainloop thread and set our context_notify_cb
        # method to be called when there's updates relating to the
        # connection to Pulseaudio
        _mainloop = pa_threaded_mainloop_new()
        _mainloop_api = pa_threaded_mainloop_get_api(_mainloop)
        context = pa_context_new(_mainloop_api, "i3pystatus_pulseaudio".encode("ascii"))

        pa_context_set_state_callback(context, self._context_notify_cb, None)
        pa_context_connect(context, None, 0, None)
        pa_threaded_mainloop_start(_mainloop)
        self.test = 1


        # self.colors = self.get_hex_color_range(self.color_muted, self.color_unmuted, 100)

        # Check that we have amixer for toggling mute/unmute and incrementing/decrementing volume
        self.has_amixer = shutil.which('alsamixer') is not None


    def request_update(self, context):
        """Requests a sink info update (sink_info_cb is called)"""
        pa_operation_unref(pa_context_get_sink_info_by_name(
            context, self.sink, self._sink_info_cb, None))

    def success_cb(self, context, success, userdata):
        pass

    def server_info_cb(self, context, server_info_p, userdata):
        """Retrieves the default sink and calls request_update"""
        server_info = server_info_p.contents
        self.sink = server_info.default_sink_name

        self.request_update(context)

    def context_notify_cb(self, context, _):
        """Checks wether the context is ready

        -Queries server information (server_info_cb is called)
        -Subscribes to property changes on all sinks (update_cb is called)
        """
        state = pa_context_get_state(context)

        if state == PA_CONTEXT_READY:
            pa_operation_unref(
                pa_context_get_server_info(context, self._server_info_cb, None))

            pa_context_set_subscribe_callback(context, self._update_cb, None)

            pa_operation_unref(pa_context_subscribe(
                context, PA_SUBSCRIPTION_EVENT_CHANGE | PA_SUBSCRIPTION_MASK_SINK | PA_SUBSCRIPTION_MASK_SERVER, self._success_cb, None))

    def update_cb(self, context, t, idx, userdata):
        """A sink property changed, calls request_update"""

        if t & PA_SUBSCRIPTION_EVENT_FACILITY_MASK == PA_SUBSCRIPTION_EVENT_SERVER:
            pa_operation_unref(
                pa_context_get_server_info(context, self._server_info_cb, None))

        self.request_update(context)

    def sink_info_cb(self, context, sink_info_p, _, __):
        """Updates self.output"""
        if sink_info_p:
            sink_info = sink_info_p.contents
            volume_percent = round(100 * sink_info.volume.values[0] / 0x10000)
            volume_db = pa_sw_volume_to_dB(sink_info.volume.values[0])
            self.currently_muted = sink_info.mute

            if volume_db == float('-Infinity'):
                volume_db = "-∞"
            else:
                volume_db = int(volume_db)

            if sink_info.mute:
                self.output = 'Muted'
            else:
                self.output = volume_percent

    def poll(self):
        return 'Vol:{}'.format(self.output)

    def switch_mute(self):
        if self.has_amixer:
            command = "amixer -q -D pulse sset Master "
            if self.currently_muted:
                command += 'unmute'
            else:
                command += 'mute'
            subprocess.Popen(command.split())

    def increase_volume(self):
        if self.has_amixer:
            command = "amixer -D pulse sset Master {}%+".format(5)
            subprocess.Popen(command.split())

    def decrease_volume(self):
        if self.has_amixer:
            command = "amixer -D pulse sset Master {}%-".format(5)
            subprocess.Popen(command.split())

    def button_press(self, x, y, button):
        if button == 5:
            self.decrease_volume()
        elif button == 4:
            self.increase_volume()
        elif button == 2:
            self.switch_mute()
