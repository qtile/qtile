# -*- coding: utf-8 -*-
import subprocess

from . import base
from .volume import BUTTON_UP, BUTTON_DOWN, BUTTON_MUTE, BUTTON_RIGHT
from ._pulse_audio import lib, ffi


@ffi.def_extern()
def qtile_pa_context_changed(context, userdata):
    widget = ffi.from_handle(userdata)
    widget.on_connection_change(context)


@ffi.def_extern()
def qtile_on_sink_info(context, info, eol, userdata):
    """called for each output sink that server has"""
    widget = ffi.from_handle(userdata)
    widget.on_sink_info(info, eol)


@ffi.def_extern()
def qtile_on_server_info(context, info, userdata):
    widget = ffi.from_handle(userdata)
    widget.on_server_info(info)


@ffi.def_extern()
def qtile_on_sink_update(context, event_type, sink_index, userdata):
    widget = ffi.from_handle(userdata)
    widget.on_sink_update(event_type, sink_index)


class PulseVolume(base.InLoopPollText):
    defaults = [
        ("step", 2, "Volume value change in percentage")
        ("volume_app", 'pavucontrol', "App to control volume"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(PulseVolume.defaults)

        self.connected = None
        self._subscribed = False
        self.default_sink_name = None
        self.default_sink = None
        self.handle = ffi.new_handle(self)

        # create a loop and api entry point
        self.loop = lib.pa_mainloop_new()
        self.api = lib.pa_mainloop_get_api(self.loop)
        # create context (e.g. connection)
        self.client_name = ffi.new('char[]', b'Qtile-pulse')
        self.context = lib.pa_context_new(self.api, self.client_name)
        self.connect()

    def __del__(self):
        lib.pa_context_disconnect(self.context)
        lib.pa_mainloop_quit(self.loop, 1)
        lib.pa_context_unref(self.context)
        lib.pa_mainloop_free(self.loop)

    def connect(self):
        lib.pa_context_connect(self.context, ffi.NULL, 0, ffi.NULL)
        lib.pa_context_set_state_callback(
            self.context,
            lib.qtile_pa_context_changed,
            self.handle
        )
        while self.connected is None:
            lib.pa_mainloop_iterate(self.loop, 1, ffi.NULL)
        self.get_server_info()

    def on_connection_change(self, context):
        """a callback from pulse lib indicating connection status"""
        state = lib.pa_context_get_state(context)
        if state == lib.PA_CONTEXT_READY:
            # ready
            self.connected = True
        elif state == lib.PA_CONTEXT_FAILED:
            # failed to connect
            self.connected = False
        elif state == lib.PA_CONTEXT_TERMINATED:
            # done
            self.connected = False

    def get_server_info(self):
        op = lib.pa_context_get_server_info(
            self.context,
            lib.qtile_on_server_info,
            self.handle
        )
        self.wait_for_operation(op)
        self.get_sinks()

    def on_server_info(self, info):
        self.default_sink_name = ffi.string(info.default_sink_name) \
            .decode('utf-8')

    def get_sinks(self):
        op = lib.pa_context_get_sink_info_list(
            self.context,
            lib.qtile_on_sink_info,
            self.handle
        )
        self.wait_for_operation(op)
        if not self._subscribed:
            self.subscribe_to_sink_events()

    def on_sink_info(self, sink, eol):
        if eol:  # dont operate on sink in case its an eol callback
            return
        name = ffi.string(sink.name).decode('utf-8')
        if name == self.default_sink_name:
            self.default_sink = {
                'name': name,
                'description': ffi.string(sink.description).decode('utf-8'),
                'index': int(sink.index),
                'base_volume': sink.base_volume,
                'muted': bool(sink.mute),
                'channels': sink.volume.channels,
                'values': list(sink.volume.values),
                'volume_steps': sink.n_volume_steps,
            }

    def subscribe_to_sink_events(self):
        op = lib.pa_context_subscribe(
            self.context,
            lib.PA_SUBSCRIPTION_MASK_SINK,
            ffi.NULL,
            ffi.NULL,
        )
        self.wait_for_operation(op)
        lib.pa_context_set_subscribe_callback(
            self.context,
            lib.qtile_on_sink_update,
            self.handle
        )
        self._subscribed = True

    def on_sink_update(self, event_type, sink_index):
        self.timeout_add(0.1, self.get_sinks)

    def wait_for_operation(self, op, unref=True):
        state = lib.pa_operation_get_state(op)
        while state == lib.PA_OPERATION_RUNNING:
            lib.pa_mainloop_iterate(self.loop, 0, ffi.NULL)
            state = lib.pa_operation_get_state(op)

    def change_volume(self, volume):
        op = lib.pa_context_set_sink_volume_by_index(
            self.context,
            self.default_sink['index'],
            volume,
            ffi.NULL,
            ffi.NULL
        )
        if op:
            self.wait_for_operation(op)

    def mute_volume(self):
        op = lib.pa_context_set_sink_mute_by_index(
            self.context,
            self.default_sink['index'],
            not self.default_sink['muted'],
            ffi.NULL,
            ffi.NULL
        )
        self.wait_for_operation(op)

    def increase_volume(self, value=2):
        if self.default_sink:
            volume = ffi.new('pa_cvolume *', {
                'channels': self.default_sink['channels'],
                'values': self.default_sink['values'],
            })
            lib.pa_cvolume_inc(
                volume,
                int(value * self.default_sink['base_volume'] / 100),
            )
            self.default_sink['values'] = list(volume.values)
            self.change_volume(volume)

    def decrease_volume(self, value=2):
        if self.default_sink:
            volume = ffi.new('pa_cvolume *', {
                'channels': self.default_sink['channels'],
                'values': self.default_sink['values'],
            })
            lib.pa_cvolume_dec(
                volume,
                int(value * self.default_sink['base_volume'] / 100),
            )
            self.default_sink['values'] = list(volume.values)
            self.change_volume(volume)

    def button_press(self, x, y, button):
        if button == BUTTON_DOWN:
            self.decrease_volume(self.step)
        elif button == BUTTON_UP:
            self.increase_volume(self.step)
        elif button == BUTTON_MUTE:
            self.mute_volume()
        elif button == BUTTON_RIGHT:
            if self.volume_app is not None:
                subprocess.Popen(self.volume_app)

        self.draw()

    def poll(self):
        lib.pa_mainloop_iterate(self.loop, 0, ffi.NULL)

        if self.default_sink:
            if self.default_sink['muted']:
                return 'M'
            base = self.default_sink['base_volume']
            if not base:
                return 'N/A'
            current = max(self.default_sink['values'])
            return str(int(current * 100 / base)) + '%'
        return 'N/A'
