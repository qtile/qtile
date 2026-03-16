#ifndef MAC_DRAWING_H
#define MAC_DRAWING_H

#include <stdbool.h>
#include <stddef.h>

struct mac_internal {
    void *win;
    void *view;
    int width;
    int height;
    void *buffer;
};

struct mac_internal *mac_internal_new(int x, int y, int width, int height);
void mac_internal_free(struct mac_internal *internal);
void mac_internal_place(struct mac_internal *internal, int x, int y, int width, int height);
void *mac_internal_get_buffer(struct mac_internal *internal);
void mac_internal_draw(struct mac_internal *internal);
void mac_internal_set_visible(struct mac_internal *internal, bool visible);
void mac_internal_bring_to_front(struct mac_internal *internal);

#endif
