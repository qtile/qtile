#ifndef LOG_H_
#define LOG_H_

#include <wlr/util/log.h>

// Callback type for forwarding wlroots log messages to external handlers
typedef void (*wrapped_log_func_t)(enum wlr_log_importance importance, const char *log_str);

// Initialize logging with specified verbosity and a custom callback to handle log messages
void qw_log_init(enum wlr_log_importance verbosity, wrapped_log_func_t callback);

#endif // LOG_H_
