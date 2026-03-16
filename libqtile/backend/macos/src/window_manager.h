#ifndef MAC_WINDOW_MANAGER_H
#define MAC_WINDOW_MANAGER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct mac_window {
    void *ptr; // AXUIElementRef
    uintptr_t wid;
};

void mac_window_retain(struct mac_window *win);
void mac_window_release(struct mac_window *win);

typedef void (*ax_observer_cb)(void *win_ptr, char *notification, void *userdata);

int mac_observer_start(ax_observer_cb callback, void *userdata);
void mac_observer_stop(void);

int mac_get_windows(struct mac_window **windows, size_t *count);
void mac_free_windows(struct mac_window *windows, size_t count);

int mac_get_focused_window(struct mac_window *win);
bool mac_is_window(void *ptr);

char *mac_window_get_name(struct mac_window *win);
char *mac_window_get_role(struct mac_window *win);
char *mac_window_get_app_name(struct mac_window *win);
char *mac_window_get_bundle_id(struct mac_window *win);

void mac_window_get_position(struct mac_window *win, int *x, int *y);
void mac_window_get_size(struct mac_window *win, int *width, int *height);
void mac_window_place(struct mac_window *win, int x, int y, int width, int height);
void mac_window_focus(struct mac_window *win);
void mac_window_bring_to_front(struct mac_window *win);
void mac_window_kill(struct mac_window *win);
void mac_window_set_hidden(struct mac_window *win, bool hidden);
int mac_window_get_pid(struct mac_window *win);
bool mac_window_is_visible(struct mac_window *win);
int mac_window_get_parent(struct mac_window *win, struct mac_window *parent_out);
void mac_window_set_fullscreen(struct mac_window *win, bool fullscreen);
void mac_window_set_maximized(struct mac_window *win, bool maximized);
void mac_window_set_minimized(struct mac_window *win, bool minimized);

#endif
