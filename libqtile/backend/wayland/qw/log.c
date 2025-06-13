#include "log.h"
#include <stdio.h>

// TODO: add pywlroots copyright

// Function pointer for Python callback to receive formatted log messages
static wrapped_log_func_t py_callback = NULL;

// Callback function passed to wlroots logging system
// Formats the log message and forwards it to the Python callback
static void qw_log_callback(enum wlr_log_importance importance, const char *fmt, va_list args) {
    char formatted_str[4096];
    vsnprintf(formatted_str, 4096, fmt, args); // Format the message safely into buffer
    py_callback(importance, formatted_str);    // Call the Python callback with formatted string
}

// Initializes wlroots logging with the specified verbosity and Python callback
void qw_log_init(enum wlr_log_importance verbosity, wrapped_log_func_t callback) {
    py_callback = callback;                   // Store Python callback for use in log handler
    wlr_log_init(verbosity, qw_log_callback); // Register our log callback with wlroots
}
