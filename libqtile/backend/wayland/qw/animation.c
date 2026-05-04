#include "animation.h"
#include "util.h"
#include "wlr/types/wlr_scene.h"
#include "xdg-view.h"
#include <threads.h>
#include <time.h>

/* Easing functions specify the rate of change of a parameter over time.
 *
 * Objects in real life don’t just start and stop instantly,
 * and almost never move at a constant speed.
 * When we open a drawer, we first move it quickly, and slow it down as it comes out.
 * Drop something on the floor, and it will first accelerate downwards,
 * and then bounce back up after hitting the floor.
 *
 * https://easings.net/#
 */

static double qw_ease_out(qw_easing_func_t ease_in, double t) { return 1.0 - ease_in(1.0 - t); }

static double qw_ease_in_out(qw_easing_func_t ease_in, double t) {
    if (t < 0.5) {
        return ease_in(2.0 * t) / 2.0;
    }

    return 1.0 - ease_in(2.0 - 2.0 * t) / 2.0;
}

/* Calculates the Y coordinate of a Cubic Bézier curve for a given time 't'.
 * Uses the Newton-Raphson numerical method to find the parametric value 'u'.
 *
 * Standard Cubic Bézier curve equation (where P0=(0,0) and P3=(1,1)):
 *   B(u) = 3*(1-u)^2 * u * P1 + 3*(1-u) * u^2 * P2 + u^3
 *
 * References:
 * - Numerical Method: https://www.geeksforgeeks.org/engineering-mathematics/newton-raphson-method/
 * - Interactive Coordinate Tool: https://cubic-bezier.com
 */
static double cubic_bezier(double x1, double y1, double x2, double y2, double t) {
    if (t <= 0.0)
        return 0.0;
    if (t >= 1.0)
        return 1.0;

    double u = t;
    // Newton-Raphson iteration to find the parametric value 'u' for time 't'
    for (int i = 0; i < 8; i++) {
        double om_u = 1.0 - u;      // 1 - u
        double om_u2 = om_u * om_u; // (1 - u)^2
        double u2 = u * u;          // u^2

        // X position on the curve at current 'u'
        double current_x = (3.0 * om_u2 * u * x1) + (3.0 * om_u * u2 * x2) + (u2 * u);

        // Derivative of X with respect to u (dx/du)
        double dx = (3.0 * om_u2 * x1) + (6.0 * om_u * u * (x2 - x1)) + (3.0 * u2 * (1.0 - x2));

        // Avoid division by zero if slope flattening occurs
        if (fabs(dx) < 1e-6)
            break;

        u -= (current_x - t) / dx;
    }

    // Clamp u safety
    if (u < 0.0)
        u = 0.0;
    if (u > 1.0)
        u = 1.0;

    // Calculate final y using the discovered u
    double om_u = 1.0 - u;
    double om_u2 = om_u * om_u;
    double u2 = u * u;

    return (3.0 * om_u2 * u * y1) + (3.0 * om_u * u2 * y2) + (u2 * u);
}

static double qw_anim_ease_out_bounce(double t) {
    if (t >= 1.0)
        return 1.0;
    if (t <= 0.0)
        return 0.0;

    const float t_scale = 2.75; // Total time units across all phases (1.0 + 1.0 + 0.5 + 0.25)
    const float g_acc = 7.5625; // Gravity acceleration coefficient (2.75 * 2.75 = 7.5625)

    /* Each bounce phase uses the standard parabola vertex form:
     *   y = a * (x - h)^2 + k
     *
     * Where:
     *   a = g_acc (gravity/steepness)
     *   h = peak time (midpoint of the current phase window / t_scale)
     *   k = peak height (1.0 minus the 75% energy decay for each bounce)
     *
     * Interactive model: https://www.desmos.com/calculator/0t2a24dcrh
     */
    if (t < (1.0 / t_scale)) {
        return g_acc * t * t;
    } else if (t < (2.0 / t_scale)) {
        t -= (1.5 / t_scale);
        return g_acc * t * t + 0.75; // k = 1.0 - 0.25
    } else if (t < (2.5 / t_scale)) {
        t -= (2.25 / t_scale);
        return g_acc * t * t + 0.9375; // k = 1.0 - 0.0625
    } else {
        t -= (2.625 / t_scale);
        return g_acc * t * t + 0.984375; // k = 1.0 - 0.015625
    }
}

static double qw_anim_ease_in_elastic(double t) {
    if (t <= 0.0) {
        return 0.0;
    }

    if (t >= 1.0) {
        return 1.0;
    }

    const double c4 = (2.0 * M_PI) / 3.0;

    return -exp2(10.0 * t - 10.0) * sin((t * 10.0 - 10.75) * c4);
}

static inline double qw_anim_ease_in_sine(double t) { return cubic_bezier(0.12, 0, 0.39, 0, t); }

static inline double qw_anim_ease_out_sine(double t) {
    return qw_ease_out(qw_anim_ease_in_sine, t);
}

static inline double qw_anim_ease_in_out_sine(double t) {
    return qw_ease_in_out(qw_anim_ease_in_sine, t);
}

static inline double qw_anim_ease_in_cubic(double t) { return t * t * t; }

static inline double qw_anim_ease_out_cubic(double t) {
    return qw_ease_out(qw_anim_ease_in_cubic, t);
}

static inline double qw_anim_ease_in_out_cubic(double t) {
    return qw_ease_in_out(qw_anim_ease_in_cubic, t);
}

static inline double qw_anim_ease_in_quint(double t) { return t * t * t * t * t; }

static inline double qw_anim_ease_out_quint(double t) {
    return qw_ease_out(qw_anim_ease_in_quint, t);
}

static inline double qw_anim_ease_in_out_quint(double t) {
    return qw_ease_in_out(qw_anim_ease_in_quint, t);
}

static inline double qw_anim_ease_in_circ(double t) { return cubic_bezier(0.55, 0, 1, 0.45, t); }

static inline double qw_anim_ease_out_circ(double t) {
    return qw_ease_out(qw_anim_ease_in_circ, t);
}

static inline double qw_anim_ease_in_out_circ(double t) {
    return qw_ease_in_out(qw_anim_ease_in_circ, t);
}

static inline double qw_anim_ease_out_elastic(double t) {
    return qw_ease_out(qw_anim_ease_in_elastic, t);
}

static inline double qw_anim_ease_in_out_elastic(double t) {
    return qw_ease_in_out(qw_anim_ease_in_elastic, t);
}

static inline double qw_anim_ease_in_quad(double t) { return t * t; }

static inline double qw_anim_ease_out_quad(double t) {
    return qw_ease_out(qw_anim_ease_in_quad, t);
}

static inline double qw_anim_ease_in_out_quad(double t) {
    return qw_ease_in_out(qw_anim_ease_in_quad, t);
}

static inline double qw_anim_ease_in_quart(double t) { return t * t * t * t; }

static inline double qw_anim_ease_out_quart(double t) {
    return qw_ease_out(qw_anim_ease_in_quart, t);
}

static inline double qw_anim_ease_in_out_quart(double t) {
    return qw_ease_in_out(qw_anim_ease_in_quart, t);
}

static inline double qw_anim_ease_in_expo(double t) { return cubic_bezier(0.7, 0, 0.84, 0, t); }
static inline double qw_anim_ease_out_expo(double t) {
    return qw_ease_out(qw_anim_ease_in_expo, t);
}

static inline double qw_anim_ease_in_out_expo(double t) {
    return qw_ease_in_out(qw_anim_ease_in_expo, t);
}

static inline double qw_anim_ease_in_back(double t) {
    const double c1 = 1.70158;
    const double c3 = c1 + 1;

    return c3 * t * t * t - c1 * t * t;
}

static inline double qw_anim_ease_out_back(double t) {
    return qw_ease_out(qw_anim_ease_in_back, t);
}

static inline double qw_anim_ease_in_out_back(double t) {
    return qw_ease_in_out(qw_anim_ease_in_back, t);
}

static inline double qw_anim_ease_in_bounce(double t) {
    // The qw_ease_out wrapper just reverses the input function
    return qw_ease_out(qw_anim_ease_out_bounce, t);
}

static inline double qw_anim_ease_in_out_bounce(double t) {
    return qw_ease_in_out(qw_anim_ease_in_bounce, t);
}

static const qw_easing_func_t qw_easing_table[QW_EASE_COUNT] = {
    // clang-format off
    [QW_EASE_IN_SINE]             = qw_anim_ease_in_sine,
    [QW_EASE_OUT_SINE]            = qw_anim_ease_out_sine,
    [QW_EASE_IN_OUT_SINE]         = qw_anim_ease_in_out_sine,

    [QW_EASE_IN_CUBIC]            = qw_anim_ease_in_cubic,
    [QW_EASE_OUT_CUBIC]           = qw_anim_ease_out_cubic,
    [QW_EASE_IN_OUT_CUBIC]        = qw_anim_ease_in_out_cubic,

    [QW_EASE_IN_QUINT]            = qw_anim_ease_in_quint,
    [QW_EASE_OUT_QUINT]           = qw_anim_ease_out_quint,
    [QW_EASE_IN_OUT_QUINT]        = qw_anim_ease_in_out_quint,

    [QW_EASE_IN_CIRC]             = qw_anim_ease_in_circ,
    [QW_EASE_OUT_CIRC]            = qw_anim_ease_out_circ,
    [QW_EASE_IN_OUT_CIRC]         = qw_anim_ease_in_out_circ,

    [QW_EASE_IN_ELASTIC]          = qw_anim_ease_in_elastic,
    [QW_EASE_OUT_ELASTIC]         = qw_anim_ease_out_elastic,
    [QW_EASE_IN_OUT_ELASTIC]      = qw_anim_ease_in_out_elastic,

    [QW_EASE_IN_QUAD]             = qw_anim_ease_in_quad,
    [QW_EASE_OUT_QUAD]            = qw_anim_ease_out_quad,
    [QW_EASE_IN_OUT_QUAD]         = qw_anim_ease_in_out_quad,

    [QW_EASE_IN_QUART]            = qw_anim_ease_in_quart,
    [QW_EASE_OUT_QUART]           = qw_anim_ease_out_quart,
    [QW_EASE_IN_OUT_QUART]        = qw_anim_ease_in_out_quart,

    [QW_EASE_IN_EXPO]             = qw_anim_ease_in_expo,
    [QW_EASE_OUT_EXPO]            = qw_anim_ease_out_expo,
    [QW_EASE_IN_OUT_EXPO]         = qw_anim_ease_in_out_expo,

    [QW_EASE_IN_BACK]             = qw_anim_ease_in_back,
    [QW_EASE_OUT_BACK]            = qw_anim_ease_out_back,
    [QW_EASE_IN_OUT_BACK]         = qw_anim_ease_in_out_back,

    [QW_EASE_IN_BOUNCE]           = qw_anim_ease_in_bounce,
    [QW_EASE_OUT_BOUNCE]          = qw_anim_ease_out_bounce,
    [QW_EASE_IN_OUT_BOUNCE]       = qw_anim_ease_in_out_bounce,
    // clang-format on
};

static qw_easing_func_t qw_anim_get_ease(qw_easing_t ease) {
    if (ease < 0 || ease >= QW_EASE_COUNT)
        return qw_anim_ease_out_quint;

    return qw_easing_table[ease];
}

static inline double qw_anim_lerp(double start, double end, double amount) {
    return start + amount * (end - start);
}

static void qw_anim_update_position(qw_anim *anim, double elapsed_ms, Vec2 *current) {
    double t = anim->duration > 0 ? elapsed_ms / anim->duration : 0;
    double eased_t = anim->ease(t);

    current->x = qw_anim_lerp(anim->start_pos.x, anim->target_pos.x, eased_t);
    current->y = qw_anim_lerp(anim->start_pos.y, anim->target_pos.y, eased_t);
}

long qw_anim_get_time_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void qw_anim_set_buffer_render_size(struct wlr_scene_buffer *buffer, int sx, int sy,
                                           void *user_data) {
    UNUSED(sx);
    UNUSED(sy);

    Vec2 *size = user_data;
    if (size->x <= 0 || size->y <= 0) {
        wlr_scene_buffer_set_dest_size(buffer, 0, 0);
    } else {
        wlr_scene_buffer_set_dest_size(buffer, (int)size->x, (int)size->y);
    }
    wlr_scene_buffer_set_filter_mode(buffer, WLR_SCALE_FILTER_BILINEAR);
}

static void qw_anim_apply_view_scale(struct qw_view *base, int w, int h) {
    Vec2 size = {.x = w, .y = h};
    wlr_scene_node_for_each_buffer(&base->content_tree->node, qw_anim_set_buffer_render_size,
                                   &size);
}

static qw_anim_progress qw_anim_get_state(qw_anim *anim) {
    qw_anim_progress c_state = {};

    c_state.now = qw_anim_get_time_ms();
    c_state.elapsed = (double)(c_state.now - anim->start_time);
    c_state.t = anim->duration > 0 ? c_state.elapsed / anim->duration : 0;
    if (c_state.t > 1.0)
        c_state.t = 1.0;
    c_state.eased_t = anim->ease(c_state.t);

    return c_state;
}

void qw_anim_setup(qw_anim *anim, struct qw_view *base, struct wlr_box target, int duration,
                   bool repos, qw_easing_t ease) {
    anim->start_pos = (Vec2){base->x, base->y};
    anim->target_pos = (Vec2){target.x, target.y};
    anim->start_time = qw_anim_get_time_ms();
    anim->start_width = base->width;
    anim->start_height = base->height;
    anim->target_width = target.width;
    anim->target_height = target.height;
    anim->duration = (double)duration;
    anim->is_active = true;
    anim->needs_scale = repos;
    anim->ease = qw_anim_get_ease(ease);
}

void qw_anim_step(struct qw_view *base) {
    if (!base->anim.is_active || !base->content_tree)
        return;

    qw_anim_progress c_state = qw_anim_get_state(&base->anim);

    Vec2 curr;
    qw_anim_update_position(&base->anim, c_state.elapsed, &curr);
    wlr_scene_node_set_position(&base->content_tree->node, (int)curr.x, (int)curr.y);

    if (base->anim.needs_scale) {
        int cur_w =
            (int)qw_anim_lerp(base->anim.start_width, base->anim.target_width, c_state.eased_t);
        int cur_h =
            (int)qw_anim_lerp(base->anim.start_height, base->anim.target_height, c_state.eased_t);
        qw_anim_apply_view_scale(base, cur_w, cur_h);
    }

    if (c_state.elapsed >= base->anim.duration) {
        wlr_scene_node_set_position(&base->content_tree->node, base->anim.target_pos.x,
                                    base->anim.target_pos.y);

        if (base->anim.needs_scale) {
            qw_anim_apply_view_scale(base, base->anim.target_width, base->anim.target_height);
        }

        if (base->on_anim_complete) {
            base->on_anim_complete(base);
        }

        base->anim.is_active = false;
        return;
    }
}

static void qw_anim_reset_bounds_invariant(struct qw_view *view, struct wlr_box *geom, int width) {
    if (geom->width > width && view->width == width) {
        view->x = 0;
        view->y = 0;
        view->width = geom->width;
        view->height = geom->height;
    }
}

static void qw_anim_update_geometry(struct qw_view *view, qw_anim_box anim_box) {
    if (anim_box.geom_dst) {
        *anim_box.geom_dst = anim_box.geom_src;
    }

    struct wlr_box t = anim_box.target;

    view->x = t.x;
    view->y = t.y;
    view->width = t.width;
    view->height = t.height;
}

void qw_anim_try_animate_resize(struct qw_view *view, qw_anim_box anim_box, int duration,
                                bool needs_scale, qw_easing_t ease) {

    qw_anim_reset_bounds_invariant(view, anim_box.geom_dst, anim_box.target.width);
    qw_anim_setup(&view->anim, view, anim_box.target, duration, needs_scale, ease);
    qw_anim_update_geometry(view, anim_box);
}

void qw_anim_kill_slide_down(struct qw_view *view, int duration, qw_easing_t ease,
                             qw_anim_cb kill_complete) {
    view->anim.is_active = false;

    // Calculate slide-down target: move window down by its height + some padding
    struct qw_output *output = qw_view_get_primary_output(view);

    int output_height;
    int target_y;
    if (output == NULL) {
        kill_complete(view);
        return;
    }

    int output_width;
    wlr_output_effective_resolution(output->wlr_output, &output_width, &output_height);

    int output_bottom = output->y + output_height;

    target_y = output_bottom;

    struct wlr_box target = {
        .x = view->x,
        .y = target_y,
        .width = view->width,
        .height = view->height,
    };

    // Slide down only (keep size)
    qw_anim_setup(&view->anim, view, target, duration, false, ease);

    // TODO: Give users ability to hack with animations
    // Slide down + scale down vertically
    // qw_anim_setup(&xdg_view->base.anim, &xdg_view->base, xdg_view->base.x, target_y,
    //              xdg_view->base.width,
    //              0,
    //              duration, true,
    //              ease);

    // Slide down + scale down both dimensions
    // qw_anim_setup(&xdg_view->base.anim, &xdg_view->base,
    //              xdg_view->base.x + xdg_view->base.width / 2,
    //              target_y,
    //              0,
    //              0,
    //              duration,
    //              true,
    //              ease);

    // Set callback to actually close the window after animation
    view->on_anim_complete = kill_complete;
}
