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

#include "extension_internal.h"

static PyObject *LOG_CALLBACK = NULL;

// Callback function passed to wlroots logging system
// Formats the log message and forwards it to the Python callback
static void qw_log_callback(enum wlr_log_importance importance, const char *fmt, va_list args) {
    char formatted_str[4096];

    (void)vsnprintf(formatted_str, sizeof(formatted_str), fmt,
                    args); // Format the message safely into buffer

    if (LOG_CALLBACK == NULL)
        return;

    PyGILState_STATE gstate = PyGILState_Ensure();

    PyObject *py_importance = PyLong_FromLong((long)importance);
    PyObject *py_msg = PyUnicode_FromString(formatted_str);
    if (!py_importance || !py_msg) {
        Py_XDECREF(py_importance);
        Py_XDECREF(py_msg);
        PyErr_Print();
        PyGILState_Release(gstate);
        return;
    }

    // Call the Python callback with formatted string
    PyObject *res = PyObject_CallFunctionObjArgs(LOG_CALLBACK, py_importance, py_msg, NULL);
    if (!res) {
        /* The callback raised — print to stderr for debugging */
        PyErr_Print();
    } else {
        Py_DECREF(res);
    }
    Py_DECREF(py_importance);
    Py_DECREF(py_msg);
    PyGILState_Release(gstate);
}

// def set_log_callback(verbosity: int, callback: Callable[[int, str], None]) -> None: ...
PyObject *py__set_log_callback(PyObject *self, PyObject *args) {
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

    wlr_log_init(verbosity, qw_log_callback);

    Py_INCREF(callback);
    return callback;
}
