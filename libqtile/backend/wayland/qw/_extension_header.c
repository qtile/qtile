#include <fcntl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/stat.h>

#include <Python.h>
#include <structmember.h>
#include <wlr/util/log.h>

static PyObject *py__hello(PyObject *, PyObject *)
{
    fprintf(stderr, "Hello, python ext!\n");
    Py_RETURN_NONE;
}

static
PyMethodDef EXPOSED_METHODS[] = {
    {"hello", py__hello, METH_VARARGS, "."},
    {NULL, NULL, 0, NULL} // sentinel
};

static
struct PyModuleDef WAYLAND_BACKEND_MODULE = {
    PyModuleDef_HEAD_INIT,
    "wayland_backend",
    "Wayland Backend Extension", // __doc__
    -1,
    EXPOSED_METHODS
};

PyMODINIT_FUNC PyInit_wayland_backend(void) // NOLINT: prefix must be PyInit_
{
    PyObject *m = PyModule_Create(&WAYLAND_BACKEND_MODULE);

    PyModule_AddIntConstant(m, "WLR_SILENT", WLR_SILENT);
    PyModule_AddIntConstant(m, "WLR_ERROR", WLR_ERROR);
    PyModule_AddIntConstant(m, "WLR_INFO", WLR_INFO);
    PyModule_AddIntConstant(m, "WLR_DEBUG", WLR_DEBUG);
    return m;
}
