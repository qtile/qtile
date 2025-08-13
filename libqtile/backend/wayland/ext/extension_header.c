#include <fcntl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/stat.h>

#include "extension_internal.h"

#include <structmember.h>
#include <wlr/util/log.h>

static PyObject *py__hello(PyObject *self, PyObject *args) {
    fprintf(stderr, "Hello, from the wayland backend extension!\n");
    Py_RETURN_NONE;
}

static PyMethodDef EXPOSED_METHODS[] = {
    {"hello", py__hello, METH_VARARGS, "dummy function"},
    {"set_log_callback", py__set_log_callback, METH_VARARGS, "set the python callback for logging"},
    {NULL, NULL, 0, NULL} // sentinel
};

// clang-format off
static struct PyModuleDef WAYLAND_BACKEND_MODULE = {
    PyModuleDef_HEAD_INIT,
    "wayland_backend",
    "Wayland Backend Extension", // __doc__
    -1, EXPOSED_METHODS
};
// clang-format on

PyMODINIT_FUNC PyInit_wayland_backend(void) // NOLINT: prefix must be PyInit_
{
    PyObject *m = PyModule_Create(&WAYLAND_BACKEND_MODULE);

    PyModule_AddIntConstant(m, "WLR_SILENT", WLR_SILENT);
    PyModule_AddIntConstant(m, "WLR_ERROR", WLR_ERROR);
    PyModule_AddIntConstant(m, "WLR_INFO", WLR_INFO);
    PyModule_AddIntConstant(m, "WLR_DEBUG", WLR_DEBUG);
    return m;
}
