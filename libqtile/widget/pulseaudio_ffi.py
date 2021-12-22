# -*- coding: utf-8 -*-
from cffi import FFI

pulseaudio_ffi = FFI()

pulseaudio_ffi.set_source(
    "libqtile.widget._pulse_audio",
    """
    #include "pulse/sample.h"
    #include "pulse/volume.h"
    #include "pulse/def.h"
    #include "pulse/introspect.h"
    #include "pulse/mainloop.h"
    #include "pulse/mainloop-api.h"
    #include "pulse/format.h"
    #include "pulse/context.h"
    #include "pulse/subscribe.h"
    """,
    libraries=["pulse"],
)

pulseaudio_ffi.cdef(
    """
    /** mainloop-api.h */
    typedef struct pa_mainloop_api pa_mainloop_api;

    /** mainloop.h */
    typedef struct pa_mainloop pa_mainloop;
    pa_mainloop *pa_mainloop_new(void);
    void pa_mainloop_free(pa_mainloop* m);
    int pa_mainloop_prepare(pa_mainloop *m, int timeout);
    int pa_mainloop_poll(pa_mainloop *m);
    int pa_mainloop_dispatch(pa_mainloop *m);
    int pa_mainloop_get_retval(pa_mainloop *m);
    int pa_mainloop_iterate(pa_mainloop *m, int block, int *retval);
    int pa_mainloop_run(pa_mainloop *m, int *retval);
    pa_mainloop_api* pa_mainloop_get_api(pa_mainloop*m);
    void pa_mainloop_quit(pa_mainloop *m, int retval);

    /** def.h */
    typedef enum pa_context_flags {
        PA_CONTEXT_NOFLAGS = ...,
        PA_CONTEXT_NOAUTOSPAWN = ...,
        PA_CONTEXT_NOFAIL = ...
    } pa_context_flags_t;
    typedef struct pa_spawn_api {
        void (*prefork)(void);
        void (*postfork)(void);
        void (*atfork)(void);
    } pa_spawn_api;
    typedef enum pa_context_state {
        PA_CONTEXT_UNCONNECTED,
        PA_CONTEXT_CONNECTING,
        PA_CONTEXT_AUTHORIZING,
        PA_CONTEXT_SETTING_NAME,
        PA_CONTEXT_READY,
        PA_CONTEXT_FAILED,
        PA_CONTEXT_TERMINATED
    } pa_context_state_t;
    typedef enum pa_operation_state {
        PA_OPERATION_RUNNING,
        PA_OPERATION_DONE,
        PA_OPERATION_CANCELLED
    } pa_operation_state_t;
    typedef enum pa_sink_flags {
        PA_SINK_NOFLAGS = ...,
        PA_SINK_HW_VOLUME_CTRL = ...,
        PA_SINK_LATENCY = ...,
        PA_SINK_HARDWARE = ...,
        PA_SINK_NETWORK = ...,
        PA_SINK_HW_MUTE_CTRL = ...,
        PA_SINK_DECIBEL_VOLUME = ...,
        PA_SINK_FLAT_VOLUME = ...,
        PA_SINK_DYNAMIC_LATENCY = ...,
        PA_SINK_SET_FORMATS = ...,
    } pa_sink_flags_t;
    typedef enum pa_sink_state {
        PA_SINK_INVALID_STATE = ...,
        PA_SINK_RUNNING = ...,
        PA_SINK_IDLE = ...,
        PA_SINK_SUSPENDED = ...,
        PA_SINK_INIT = ...,
        PA_SINK_UNLINKED = ...
    } pa_sink_state_t;


    typedef enum pa_subscription_mask {
        PA_SUBSCRIPTION_MASK_NULL = ...,
        /**< No events */

        PA_SUBSCRIPTION_MASK_SINK = ...,
        /**< Sink events */

        PA_SUBSCRIPTION_MASK_SOURCE = ...,
        /**< Source events */

        PA_SUBSCRIPTION_MASK_SINK_INPUT = ...,
        /**< Sink input events */

        PA_SUBSCRIPTION_MASK_SOURCE_OUTPUT = ...,
        /**< Source output events */

        PA_SUBSCRIPTION_MASK_MODULE = ...,
        /**< Module events */

        PA_SUBSCRIPTION_MASK_CLIENT = ...,
        /**< Client events */

        PA_SUBSCRIPTION_MASK_SAMPLE_CACHE = ...,
        /**< Sample cache events */

        PA_SUBSCRIPTION_MASK_SERVER = ...,
        /**< Other global server changes. */

        PA_SUBSCRIPTION_MASK_AUTOLOAD = ...,
        /** deprecated Autoload table events. */

        PA_SUBSCRIPTION_MASK_CARD = ...,
        /** Card events. since 0.9.15 */

        PA_SUBSCRIPTION_MASK_ALL = ...,
        /**< Catch all events */
    } pa_subscription_mask_t;

    /** Subscription event types, as used by pa_context_subscribe() */
    typedef enum pa_subscription_event_type {
        PA_SUBSCRIPTION_EVENT_SINK = ...,
        /**< Event type: Sink */

        PA_SUBSCRIPTION_EVENT_SOURCE = ...,
        /**< Event type: Source */

        PA_SUBSCRIPTION_EVENT_SINK_INPUT = ...,
        /**< Event type: Sink input */

        PA_SUBSCRIPTION_EVENT_SOURCE_OUTPUT = ...,
        /**< Event type: Source output */

        PA_SUBSCRIPTION_EVENT_MODULE = ...,
        /**< Event type: Module */

        PA_SUBSCRIPTION_EVENT_CLIENT = ...,
        /**< Event type: Client */

        PA_SUBSCRIPTION_EVENT_SAMPLE_CACHE = ...,
        /**< Event type: Sample cache item */

        PA_SUBSCRIPTION_EVENT_SERVER = ...,
        /**< Event type: Global server change, only occurring with PA_SUBSCRIPTION_EVENT_CHANGE. */

        PA_SUBSCRIPTION_EVENT_AUTOLOAD = ...,
        /** deprecated Event type: Autoload table changes. */

        PA_SUBSCRIPTION_EVENT_CARD = ...,
        /**< Event type: Card since 0.9.15 */

        PA_SUBSCRIPTION_EVENT_FACILITY_MASK = ...,
        /**< A mask to extract the event type from an event value */

        PA_SUBSCRIPTION_EVENT_NEW = ...,
        /**< A new object was created */

        PA_SUBSCRIPTION_EVENT_CHANGE = ...,
        /**< A property of the object was modified */

        PA_SUBSCRIPTION_EVENT_REMOVE = ...,
        /**< An object was removed */

        PA_SUBSCRIPTION_EVENT_TYPE_MASK = ...,
        /**< A mask to extract the event operation from an event value */

    } pa_subscription_event_type_t;

    /** context.h */
    typedef struct pa_context pa_context;
    typedef void (*pa_context_notify_cb_t)(pa_context *c, void *userdata);
    typedef void (*pa_context_success_cb_t) (pa_context *c, int success, void *userdata);
    pa_context *pa_context_new(pa_mainloop_api *mainloop, const char *name);
    int pa_context_connect(pa_context *c, const char *server, pa_context_flags_t flags, const pa_spawn_api *api);
    void pa_context_set_state_callback(pa_context *c, pa_context_notify_cb_t cb, void *userdata);
    pa_context_state_t pa_context_get_state(pa_context *c);
    void pa_context_disconnect(pa_context *c);
    void pa_context_unref(pa_context *c);

    /** channelmap.h */
    typedef enum pa_channel_position {
        PA_CHANNEL_POSITION_INVALID = ...,
        PA_CHANNEL_POSITION_MONO = ...,

        PA_CHANNEL_POSITION_FRONT_LEFT,
        PA_CHANNEL_POSITION_FRONT_RIGHT,
        PA_CHANNEL_POSITION_FRONT_CENTER,

        PA_CHANNEL_POSITION_LEFT = PA_CHANNEL_POSITION_FRONT_LEFT,
        PA_CHANNEL_POSITION_RIGHT = PA_CHANNEL_POSITION_FRONT_RIGHT,
        PA_CHANNEL_POSITION_CENTER = PA_CHANNEL_POSITION_FRONT_CENTER,

        PA_CHANNEL_POSITION_REAR_CENTER,
        PA_CHANNEL_POSITION_REAR_LEFT,
        PA_CHANNEL_POSITION_REAR_RIGHT,

        PA_CHANNEL_POSITION_LFE,
        PA_CHANNEL_POSITION_SUBWOOFER = PA_CHANNEL_POSITION_LFE,

        PA_CHANNEL_POSITION_FRONT_LEFT_OF_CENTER,
        PA_CHANNEL_POSITION_FRONT_RIGHT_OF_CENTER,

        PA_CHANNEL_POSITION_SIDE_LEFT,
        PA_CHANNEL_POSITION_SIDE_RIGHT,

        PA_CHANNEL_POSITION_AUX0,
        PA_CHANNEL_POSITION_AUX1,
        PA_CHANNEL_POSITION_AUX2,
        PA_CHANNEL_POSITION_AUX3,
        PA_CHANNEL_POSITION_AUX4,
        PA_CHANNEL_POSITION_AUX5,
        PA_CHANNEL_POSITION_AUX6,
        PA_CHANNEL_POSITION_AUX7,
        PA_CHANNEL_POSITION_AUX8,
        PA_CHANNEL_POSITION_AUX9,
        PA_CHANNEL_POSITION_AUX10,
        PA_CHANNEL_POSITION_AUX11,
        PA_CHANNEL_POSITION_AUX12,
        PA_CHANNEL_POSITION_AUX13,
        PA_CHANNEL_POSITION_AUX14,
        PA_CHANNEL_POSITION_AUX15,
        PA_CHANNEL_POSITION_AUX16,
        PA_CHANNEL_POSITION_AUX17,
        PA_CHANNEL_POSITION_AUX18,
        PA_CHANNEL_POSITION_AUX19,
        PA_CHANNEL_POSITION_AUX20,
        PA_CHANNEL_POSITION_AUX21,
        PA_CHANNEL_POSITION_AUX22,
        PA_CHANNEL_POSITION_AUX23,
        PA_CHANNEL_POSITION_AUX24,
        PA_CHANNEL_POSITION_AUX25,
        PA_CHANNEL_POSITION_AUX26,
        PA_CHANNEL_POSITION_AUX27,
        PA_CHANNEL_POSITION_AUX28,
        PA_CHANNEL_POSITION_AUX29,
        PA_CHANNEL_POSITION_AUX30,
        PA_CHANNEL_POSITION_AUX31,

        PA_CHANNEL_POSITION_TOP_CENTER,

        PA_CHANNEL_POSITION_TOP_FRONT_LEFT,
        PA_CHANNEL_POSITION_TOP_FRONT_RIGHT,
        PA_CHANNEL_POSITION_TOP_FRONT_CENTER,

        PA_CHANNEL_POSITION_TOP_REAR_LEFT,
        PA_CHANNEL_POSITION_TOP_REAR_RIGHT,
        PA_CHANNEL_POSITION_TOP_REAR_CENTER,

        PA_CHANNEL_POSITION_MAX
    } pa_channel_position_t;
    typedef struct pa_channel_map {
        uint8_t channels;
        pa_channel_position_t map[...];
    } pa_channel_map;

    /** sample.h */
    #define PA_CHANNELS_MAX  ...
    typedef enum pa_sample_format {
        PA_SAMPLE_U8,
        PA_SAMPLE_ALAW,
        PA_SAMPLE_ULAW,
        PA_SAMPLE_S16LE,
        PA_SAMPLE_S16BE,
        PA_SAMPLE_FLOAT32LE,
        PA_SAMPLE_FLOAT32BE,
        PA_SAMPLE_S32LE,
        PA_SAMPLE_S32BE,
        PA_SAMPLE_S24LE,
        PA_SAMPLE_S24BE,
        PA_SAMPLE_S24_32LE,
        PA_SAMPLE_S24_32BE,
        PA_SAMPLE_MAX,
        PA_SAMPLE_INVALID = -1
    } pa_sample_format_t;
    typedef struct pa_sample_spec {
        pa_sample_format_t format;
        uint32_t rate;
        uint8_t channels;
    } pa_sample_spec;
    typedef uint64_t pa_usec_t;

    /** operation.h */
    typedef struct pa_operation pa_operation;
    pa_operation_state_t pa_operation_get_state(pa_operation *o);

    /** volume.h */
    #define PA_VOLUME_NORM ...
    #define PA_VOLUME_MUTED ...
    #define PA_VOLUME_MAX ...
    #define PA_CHANNELS_MAX ...

    typedef uint32_t pa_volume_t;
    typedef struct {
        uint8_t channels;
        pa_volume_t values[...];
    } pa_cvolume;

    pa_cvolume* pa_cvolume_init(pa_cvolume *a);
    int pa_cvolume_valid(const pa_cvolume *v);
    pa_cvolume* pa_cvolume_scale(pa_cvolume *v, pa_volume_t max);
    pa_volume_t pa_cvolume_avg(const pa_cvolume *a);
    pa_volume_t pa_cvolume_max(const pa_cvolume *a);
    pa_cvolume* pa_cvolume_inc(pa_cvolume *v, pa_volume_t inc);
    pa_cvolume* pa_cvolume_dec(pa_cvolume *v, pa_volume_t dec);
    pa_cvolume* pa_cvolume_set(pa_cvolume *a, unsigned channels, pa_volume_t v);

    int pa_cvolume_channels_equal_to(const pa_cvolume *a, pa_volume_t v);
    char *pa_cvolume_snprint(char *s, size_t l, const pa_cvolume *c);

    /** proplist.h */
    typedef struct pa_proplist pa_proplist;

    /** format.h */
    typedef enum pa_encoding {
        PA_ENCODING_ANY,
        PA_ENCODING_PCM,
        PA_ENCODING_AC3_IEC61937,
        PA_ENCODING_EAC3_IEC61937,
        PA_ENCODING_MPEG_IEC61937,
        PA_ENCODING_DTS_IEC61937,
        PA_ENCODING_MPEG2_AAC_IEC61937,
        PA_ENCODING_MAX,
        PA_ENCODING_INVALID = ...
    } pa_encoding_t;
    typedef struct pa_format_info {
        pa_encoding_t encoding;
        pa_proplist *plist;
    } pa_format_info;

    /** introspect.h */
    typedef struct pa_sink_port_info {
        const char *name;
        const char *description;
        uint32_t priority;
        int available;
    } pa_sink_port_info;
    typedef struct pa_sink_info {
        const char *name;
        uint32_t index;
        const char *description;
        pa_sample_spec sample_spec;
        pa_channel_map channel_map;
        uint32_t owner_module;
        pa_cvolume volume;
        int mute;
        uint32_t monitor_source;
        const char *monitor_source_name;
        pa_usec_t latency;
        const char *driver;
        pa_sink_flags_t flags;
        pa_proplist *proplist;
        pa_usec_t configured_latency;
        pa_volume_t base_volume;
        pa_sink_state_t state;
        uint32_t n_volume_steps;
        uint32_t card;
        uint32_t n_ports;
        pa_sink_port_info** ports;
        pa_sink_port_info* active_port;
        uint8_t n_formats;
        pa_format_info **formats;
    } pa_sink_info;

    typedef void (*pa_sink_info_cb_t)(pa_context *c, const pa_sink_info *i, int eol, void *userdata);
    pa_operation* pa_context_get_sink_info_list(pa_context *c, pa_sink_info_cb_t cb, void *userdata);

    typedef struct pa_server_info {
        const char *user_name;
        const char *host_name;
        const char *server_version;
        const char *server_name;
        pa_sample_spec sample_spec;
        const char *default_sink_name;
        const char *default_source_name;
        uint32_t cookie;
        pa_channel_map channel_map;
    } pa_server_info;
    typedef void (*pa_server_info_cb_t) (pa_context *c, const pa_server_info*i, void *userdata);
    pa_operation* pa_context_get_server_info(pa_context *c, pa_server_info_cb_t cb, void *userdata);


    pa_operation* pa_context_set_sink_volume_by_index(
        pa_context *c, uint32_t idx, const pa_cvolume *volume, pa_context_success_cb_t cb, void *userdata);
    pa_operation* pa_context_set_sink_volume_by_name(
        pa_context *c, const char *name, const pa_cvolume *volume, pa_context_success_cb_t cb, void *userdata);
    pa_operation* pa_context_set_sink_mute_by_index(
        pa_context *c, uint32_t idx, int mute, pa_context_success_cb_t cb, void *userdata);
    pa_operation* pa_context_set_sink_mute_by_name(
        pa_context *c, const char *name, int mute, pa_context_success_cb_t cb, void *userdata);

    /** subscribe.h */
    /** Subscription event callback prototype */
    typedef void (*pa_context_subscribe_cb_t)(
        pa_context *c, pa_subscription_event_type_t t, uint32_t idx, void *userdata);

    /** Enable event notification */
    pa_operation* pa_context_subscribe(
        pa_context *c, pa_subscription_mask_t m, pa_context_success_cb_t cb, void *userdata);

    /** Set the context specific call back function that is called whenever the state of the daemon changes */
    void pa_context_set_subscribe_callback(pa_context *c, pa_context_subscribe_cb_t cb, void *userdata);



    /** python callbacks */
    extern "Python" void qtile_pa_context_changed(pa_context *c, void *userdata);
    extern "Python" void qtile_on_sink_info(pa_context *c, const pa_sink_info *i, int eol, void *userdata);
    extern "Python" void qtile_on_server_info(pa_context *c, const pa_server_info*i, void *userdata);
    extern "Python" void qtile_on_sink_update(
        pa_context *c, pa_subscription_event_type_t t, uint32_t idx, void *userdata);

"""
)

if __name__ == "__main__":
    pulseaudio_ffi.compile()
