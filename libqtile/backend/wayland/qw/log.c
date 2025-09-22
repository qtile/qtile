/*
 * Copyright (c) 2018 Sean Vig
 *
 * This file contains code copied or adapted from pywlroots,
 * which is licensed under the MIT License.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights to
 * use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
 * of the Software, and to permit persons to whom the Software is furnished to do
 * so, subject to the following conditions:
 *
 * - Redistributions of source code must retain the above copyright notice, this
 *   list of conditions and the following disclaimers.
 *
 * - Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimers in the documentation
 *   and/or other materials provided with the distribution.
 *
 * - Neither the names of the developers nor the names of its contributors may be
 *   used to endorse or promote products derived from this Software without
 *   specific prior written permission.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * Modifications Copyright (c) 2025 The Qtile Project
 *
 * Licensed under the MIT License.
 * See the LICENSE file in the root of this repository for details.
 */

#include "log.h"
#include <stdio.h>

// Function pointer for Python callback to receive formatted log messages
static wrapped_log_func_t py_callback = NULL;

// Callback function passed to wlroots logging system
// Formats the log message and forwards it to the Python callback
static void qw_log_callback(enum wlr_log_importance importance, const char *fmt, va_list args) {
    char formatted_str[4096];

    (void)vsnprintf(formatted_str, sizeof(formatted_str), fmt,
                    args);                  // Format the message safely into buffer
    py_callback(importance, formatted_str); // Call the Python callback with formatted string
}

// Initializes wlroots logging with the specified verbosity and Python callback
void qw_log_init(enum wlr_log_importance verbosity, wrapped_log_func_t callback) {
    py_callback = callback;                   // Store Python callback for use in log handler
    wlr_log_init(verbosity, qw_log_callback); // Register our log callback with wlroots
}
