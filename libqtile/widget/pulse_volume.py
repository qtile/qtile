# -*- coding: utf-8 -*-
import logging

from libqtile.widget._pulse_audio import ffi, lib
from libqtile.widget.volume import Volume

log = logging.getLogger(__name__)


@ffi.def_extern()
def qtile_pa_context_changed(context, userdata):
    """callback for connecting status update"""
    widget = ffi.from_handle(userdata)
    widget.on_connection_change(context)


@ffi.def_extern()
def qtile_on_sink_info(context, info, eol, userdata):
    """callback for each output sink that pulseaudio server has"""
    widget = ffi.from_handle(userdata)
    widget.on_sink_info(info, eol)


@ffi.def_extern()
def qtile_on_server_info(context, info, userdata):
    """callback with a pulseaudio server info"""
    widget = ffi.from_handle(userdata)
    widget.on_server_info(info)


@ffi.def_extern()
def qtile_on_sink_update(context, event_type, sink_index, userdata):
    """callback for updates made to sinks"""
    widget = ffi.from_handle(userdata)
    widget.on_sink_update(event_type, sink_index)


class PulseVolume(Volume):
    defaults = [
        ("limit_max_volume", False, "Limit maximum volume to 100%"),
    ]

    def __init__(self, **config):
        Volume.__init__(self, **config)
        self.add_defaults(PulseVolume.defaults)

        self.connected = None
        self._subscribed = False
        self.default_sink_name = None
        self.default_sink = None
        self.handle = ffi.new_handle(self)
        self.client_name = ffi.new("char[]", b"Qtile-pulse")

        self.connect()

    def finalize(self):
        lib.pa_context_disconnect(self.context)
        lib.pa_mainloop_quit(self.loop, 1)
        lib.pa_context_unref(self.context)
        lib.pa_mainloop_free(self.loop)
        Volume.finalize(self)

    def connect(self):
        """
        issue a connection to pulse audio server. result of a connection
        would be passed to `on_connection_change` method
        """
        # create a loop and api entry point
        self.loop = lib.pa_mainloop_new()
        self.api = lib.pa_mainloop_get_api(self.loop)
        # create context (e.g. connection)
        self.context = lib.pa_context_new(self.api, self.client_name)
        lib.pa_context_connect(self.context, ffi.NULL, 0, ffi.NULL)
        lib.pa_context_set_state_callback(self.context, lib.qtile_pa_context_changed, self.handle)

    def on_connection_change(self, context):
        """a callback from pulse lib indicating connection status"""
        state = lib.pa_context_get_state(context)
        if state == lib.PA_CONTEXT_READY:
            # ready
            self.connected = True
            # once onnection is established we need to get server information
            self.timeout_add(0.1, self.get_server_info)
            log.debug("Connection to pulseaudio ready")
        elif state == lib.PA_CONTEXT_FAILED:
            # failed to connect
            self.connected = False
            self._subscribed = False
            log.warning("Failed to connect to pulseaudio, retrying in 10s")
            self.timeout_add(10, self.connect)
        elif state == lib.PA_CONTEXT_TERMINATED:
            # done
            self.connected = False
            self._subscribed = False
            log.debug("Connection to pulseaudio terminated cleanly")
        elif state == lib.PA_CONTEXT_UNCONNECTED:
            self.connected = False
            self._subscribed = False
            log.warning("Disconnected from pulseaudio")

    def get_server_info(self):
        lib.pa_context_get_server_info(self.context, lib.qtile_on_server_info, self.handle)

    def on_server_info(self, info):
        self.default_sink_name = ffi.string(info.default_sink_name).decode("utf-8")
        self.timeout_add(0.1, self.get_sinks)

    def get_sinks(self):
        lib.pa_context_get_sink_info_list(self.context, lib.qtile_on_sink_info, self.handle)

    def on_sink_info(self, sink, eol):
        if eol:  # dont operate on sink in case its an eol callback
            if not self._subscribed:
                self.timeout_add(0.1, self.subscribe_to_sink_events)
            return
        name = ffi.string(sink.name).decode("utf-8")
        if name == self.default_sink_name:
            self.default_sink = {
                "name": name,
                "description": ffi.string(sink.description).decode("utf-8"),
                "index": int(sink.index),
                "base_volume": sink.base_volume,
                "muted": bool(sink.mute),
                "channels": sink.volume.channels,
                "values": list(sink.volume.values),
            }
            self.update()

    def subscribe_to_sink_events(self):
        op = lib.pa_context_subscribe(
            self.context,
            lib.PA_SUBSCRIPTION_MASK_SINK,
            ffi.NULL,
            ffi.NULL,
        )
        self.wait_for_operation(op)
        lib.pa_context_set_subscribe_callback(self.context, lib.qtile_on_sink_update, self.handle)
        self._subscribed = True

    def on_sink_update(self, event_type, sink_index):
        self.timeout_add(0.1, self.get_sinks)

    def wait_for_operation(self, op):
        state = lib.pa_operation_get_state(op)
        while state == lib.PA_OPERATION_RUNNING:
            lib.pa_mainloop_iterate(self.loop, 0, ffi.NULL)
            state = lib.pa_operation_get_state(op)

    def change_volume(self, volume):
        """
        order pulseaudio to apply new volume
        """
        # store new volume to "speed up" widget update so that we don't have
        # to wait a callback from pulseaudio
        self.default_sink["values"] = list(volume.values)
        op = lib.pa_context_set_sink_volume_by_index(
            self.context, self.default_sink["index"], volume, ffi.NULL, ffi.NULL
        )
        if op:
            self.wait_for_operation(op)

    def cmd_mute(self):
        op = lib.pa_context_set_sink_mute_by_index(
            self.context,
            self.default_sink["index"],
            not self.default_sink["muted"],
            ffi.NULL,
            ffi.NULL,
        )
        if op:
            self.wait_for_operation(op)

    def cmd_increase_vol(self, value=None):
        if value is None:
            value = self.step
        base = self.default_sink["base_volume"]
        volume = ffi.new(
            "pa_cvolume *",
            {
                "channels": self.default_sink["channels"],
                "values": self.default_sink["values"],
            },
        )
        lib.pa_cvolume_inc(
            volume,
            int(value * base / 100),
        )
        # check that we dont go over 100% in case its set in config
        if self.limit_max_volume:
            volume.values = [(i if i <= base else base) for i in volume.values]
        self.change_volume(volume)

    def cmd_decrease_vol(self, value=None):
        if value is None:
            value = self.step
        volume_level = int(value * self.default_sink["base_volume"] / 100)
        if not volume_level and max(self.default_sink["values"]) == 0:
            # can't be lower than zero
            return
        volume = ffi.new(
            "pa_cvolume *",
            {
                "channels": self.default_sink["channels"],
                "values": self.default_sink["values"],
            },
        )
        lib.pa_cvolume_dec(volume, volume_level)
        self.change_volume(volume)

    def button_press(self, x, y, button):
        Volume.button_press(self, x, y, button)
        self.poll()

    def poll(self):
        lib.pa_mainloop_iterate(self.loop, 0, ffi.NULL)
        self.update()

    def update(self):
        """
        same method as in Volume widgets except that here we don't need to
        manually re-schedule update
        """
        vol = self.get_volume()
        if vol != self.volume:
            self.volume = vol
            # Update the underlying canvas size before actually attempting
            # to figure out how big it is and draw it.
            self._update_drawer()
            self.bar.draw()

    def get_volume(self):
        if self.default_sink:
            if self.default_sink["muted"]:
                return -1
            base = self.default_sink["base_volume"]
            if not base:
                return -1
            current = max(self.default_sink["values"])
            return round(current * 100 / base)
        return -1

    def timer_setup(self):
        self.poll()
        if self.update_interval is not None:
            self.timeout_add(self.update_interval, self.timer_setup)
        if self.theme_path:
            self.setup_images()
