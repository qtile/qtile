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

#if defined(WAYLAND_BACKEND_EXTENSION)
    #include "_extension_internal.h"

static PyObject *LOG_CALLBACK = NULL;

static
void log_callback(enum wlr_log_importance importance, const char *fmt, va_list args)
{
    if (!LOG_CALLBACK) {
        return; // No callback registered
    }

#define LOG_BUFFER_SZ 4096

    char formatted_str[LOG_BUFFER_SZ];
    vsnprintf(formatted_str, LOG_BUFFER_SZ, fmt, args);

    PyGILState_STATE gstate = PyGILState_Ensure();
    PyObject *result = PyObject_CallFunction(LOG_CALLBACK, "is", importance, formatted_str);
    if (!result) {
        PyErr_Print();
    }

    Py_XDECREF(result);
    PyGILState_Release(gstate);
}

// def set_log_callback(verbosity: int, callback: Callable[[int, str], None]) -> None: ...
PyObject *py__set_log_callback(PyObject *self, PyObject *args)
{
    int verbosity;
    PyObject *callback;

    if (!PyArg_ParseTuple(args, "iO:set_log_callback", &verbosity, &callback)) {
        return NULL;
    }

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "Parameter must be callable");
        return NULL;
    }

    Py_XINCREF(callback);
    Py_XDECREF(LOG_CALLBACK);
    LOG_CALLBACK = callback;

    wlr_log_init(verbosity, log_callback);

    Py_INCREF(callback);
    return callback; // Return the callback itself (decorator style)
}

#endif
