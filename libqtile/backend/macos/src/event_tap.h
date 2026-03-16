#include <stdbool.h>
#include <stdint.h>

typedef int (*event_tap_cb)(uint32_t type, uint64_t flags, uint32_t keycode, void *userdata);

int mac_event_tap_start(event_tap_cb callback, void *userdata);
void mac_event_tap_stop(void);
double mac_get_idle_time(void);
