#ifndef ANIMATION_H
#define ANIMATION_H

#include <stdbool.h>
#include <wlr/util/box.h>

struct qw_xdg_view;
struct qw_xwayland_view;
struct qw_view;

typedef enum {
    QW_EASE_IN_SINE,
    QW_EASE_OUT_SINE,
    QW_EASE_IN_OUT_SINE,
    QW_EASE_IN_CUBIC,
    QW_EASE_OUT_CUBIC,
    QW_EASE_IN_OUT_CUBIC,
    QW_EASE_IN_QUINT,
    QW_EASE_OUT_QUINT,
    QW_EASE_IN_OUT_QUINT,
    QW_EASE_IN_CIRC,
    QW_EASE_OUT_CIRC,
    QW_EASE_IN_OUT_CIRC,
    QW_EASE_IN_ELASTIC,
    QW_EASE_OUT_ELASTIC,
    QW_EASE_IN_OUT_ELASTIC,
    QW_EASE_IN_QUAD,
    QW_EASE_OUT_QUAD,
    QW_EASE_IN_OUT_QUAD,
    QW_EASE_IN_QUART,
    QW_EASE_OUT_QUART,
    QW_EASE_IN_OUT_QUART,
    QW_EASE_IN_EXPO,
    QW_EASE_OUT_EXPO,
    QW_EASE_IN_OUT_EXPO,
    QW_EASE_IN_BACK,
    QW_EASE_OUT_BACK,
    QW_EASE_IN_OUT_BACK,
    QW_EASE_IN_BOUNCE,
    QW_EASE_OUT_BOUNCE,
    QW_EASE_IN_OUT_BOUNCE,
    QW_EASE_COUNT
} qw_easing_t;

typedef double (*qw_easing_func_t)(double t);

typedef struct {
    int x, y;
} Vec2;

typedef struct {
    bool is_active;
    bool needs_scale;
    size_t start_time;
    Vec2 start_pos;
    Vec2 target_pos;
    int start_width;
    int start_height;
    int target_width;
    int target_height;
    double duration;
    qw_easing_func_t ease;
} qw_anim;

typedef struct {
    struct wlr_box *geom_dst;
    struct wlr_box geom_src;
    struct wlr_box target;
} qw_anim_box;

// Capture time states for the animation
typedef struct {
    size_t now;
    double elapsed;
    double t;
    double eased_t;
} qw_anim_progress;

typedef void (*qw_anim_cb)(struct qw_view *self);

long qw_anim_get_time_ms();
void qw_anim_step(struct qw_view *base);
void qw_anim_setup(qw_anim *anim, struct qw_view *base, struct wlr_box target, int duration,
                   bool repos, qw_easing_t ease);
void qw_anim_try_animate_resize(struct qw_view *view, qw_anim_box anim_box, int duration,
                                bool needs_repos, qw_easing_t ease);
void qw_anim_kill_slide_down(struct qw_view *view, int duration, qw_easing_t ease,
                             qw_anim_cb kill_complete);

#endif
