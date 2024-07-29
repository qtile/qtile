#include "log.h"
#include <stdio.h>

// TODO: add pywlroots copyright
static wrapped_log_func_t py_callback = NULL;
static void qw_log_callback(enum wlr_log_importance importance, const char *fmt, va_list args) {
    char formatted_str[4096];
    vsnprintf(formatted_str, 4096, fmt, args);
    py_callback(importance, formatted_str);
}

void qw_log_init(enum wlr_log_importance verbosity, wrapped_log_func_t callback) {
    py_callback = callback;
    wlr_log_init(verbosity, qw_log_callback);
}
