#include "pointer.h"
#include "util.h"

#include <math.h>
#include <wlr/types/wlr_pointer.h>

static uint32_t qw_pointer_get_keyboard_modifiers(struct qw_server *server) {
    struct wlr_keyboard *kb = wlr_seat_get_keyboard(server->seat);
    if (kb == NULL) {
        wlr_log(WLR_INFO, "No active keyboard found, gesture may be missed");
        return 0;
    }

    return wlr_keyboard_get_modifiers(kb);
}

static void qw_pointer_handle_swipe_begin(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_pointer *pointer = wl_container_of(listener, pointer, swipe_begin);
    pointer->swipe_sequence = calloc(1, sizeof(struct qw_swipe_sequence));
}

static void qw_pointer_handle_swipe_update(struct wl_listener *listener, void *data) {
    struct qw_pointer *pointer = wl_container_of(listener, pointer, swipe_update);
    struct qw_swipe_sequence *swipe_sequence = pointer->swipe_sequence;

    if (swipe_sequence == NULL) {
        return;
    }
    struct wlr_pointer_swipe_update_event *event = data;

    if (fabs(event->dx) < 5.0 && fabs(event->dy) < 5.0)
        return;

    char dir;
    if (fabs(event->dx) > fabs(event->dy)) {
        dir = event->dx > 0 ? 'R' : 'L';
    } else {
        dir = event->dy > 0 ? 'D' : 'U';
    }

    // append only if different from the last direction in the sequence
    if (swipe_sequence->length == 0 ||
        swipe_sequence->sequence[swipe_sequence->length - 1] != dir) {
        if (swipe_sequence->length < sizeof(swipe_sequence->sequence))
            swipe_sequence->sequence[swipe_sequence->length++] = dir;
    }
}

static void qw_pointer_handle_swipe_end(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_pointer *pointer = wl_container_of(listener, pointer, swipe_end);
    struct qw_server *server = pointer->server;
    struct qw_swipe_sequence *swipe_sequence = pointer->swipe_sequence;
    if (swipe_sequence == NULL) {
        return;
    }

    if (swipe_sequence->length > 0) {
        uint32_t mask = qw_pointer_get_keyboard_modifiers(server);
        server->pointer_swipe_cb(mask, swipe_sequence->sequence, server->cb_data);
    }

    free(swipe_sequence);
    pointer->swipe_sequence = NULL;
}

static void qw_pointer_handle_pinch_begin(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_pointer *pointer = wl_container_of(listener, pointer, pinch_begin);
    pointer->pinch = calloc(1, sizeof(struct qw_pinch));
    pointer->pinch->rotation = 0;
    pointer->pinch->scale = 1;
}

static void qw_pointer_handle_pinch_update(struct wl_listener *listener, void *data) {
    struct qw_pointer *pointer = wl_container_of(listener, pointer, pinch_update);
    struct qw_pinch *pinch = pointer->pinch;

    if (pinch == NULL) {
        return;
    }

    struct wlr_pointer_pinch_update_event *event = data;
    pinch->scale = event->scale;
    pinch->rotation += event->rotation;
}

static void qw_pointer_handle_pinch_end(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_pointer *pointer = wl_container_of(listener, pointer, pinch_end);
    struct qw_server *server = pointer->server;
    struct qw_pinch *pinch = pointer->pinch;

    if (pinch == NULL) {
        return;
    }

    uint32_t mask = qw_pointer_get_keyboard_modifiers(server);
    bool shrink = (pinch->scale < 1);
    bool clockwise = (pinch->rotation > 0);
    server->pointer_pinch_cb(mask, shrink, clockwise, server->cb_data);

    free(pinch);
    pointer->pinch = NULL;
}

static void qw_pointer_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_pointer *pointer = wl_container_of(listener, pointer, destroy);

    if (pointer->swipe_sequence != NULL) {
        free(pointer->swipe_sequence);
    }

    if (pointer->pinch != NULL) {
        free(pointer->pinch);
    }

    wl_list_remove(&pointer->swipe_begin.link);
    wl_list_remove(&pointer->swipe_update.link);
    wl_list_remove(&pointer->swipe_end.link);
    wl_list_remove(&pointer->pinch_begin.link);
    wl_list_remove(&pointer->pinch_update.link);
    wl_list_remove(&pointer->pinch_end.link);
    wl_list_remove(&pointer->destroy.link);
    wl_list_remove(&pointer->link);
    free(pointer);
}

void qw_pointer_handle_new(struct qw_server *server, struct wlr_input_device *device) {
    struct wlr_pointer *pointer = wlr_pointer_from_input_device(device);

    struct qw_pointer *p = calloc(1, sizeof(*p));
    p->server = server;
    p->device = device;
    wl_list_insert(&server->pointers, &p->link);

    // Attach gesture listeners
    p->swipe_begin.notify = qw_pointer_handle_swipe_begin;
    wl_signal_add(&pointer->events.swipe_begin, &p->swipe_begin);

    p->swipe_update.notify = qw_pointer_handle_swipe_update;
    wl_signal_add(&pointer->events.swipe_update, &p->swipe_update);

    p->swipe_end.notify = qw_pointer_handle_swipe_end;
    wl_signal_add(&pointer->events.swipe_end, &p->swipe_end);

    p->pinch_begin.notify = qw_pointer_handle_pinch_begin;
    wl_signal_add(&pointer->events.pinch_begin, &p->pinch_begin);

    p->pinch_update.notify = qw_pointer_handle_pinch_update;
    wl_signal_add(&pointer->events.pinch_update, &p->pinch_update);

    p->pinch_end.notify = qw_pointer_handle_pinch_end;
    wl_signal_add(&pointer->events.pinch_end, &p->pinch_end);

    p->destroy.notify = qw_pointer_handle_destroy;
    wl_signal_add(&device->events.destroy, &p->destroy);
}
