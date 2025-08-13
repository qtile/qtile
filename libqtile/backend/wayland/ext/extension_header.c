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
    {NULL, NULL, 0, NULL}
};

static
struct PyModuleDef WAYLAND_BACKEND_MODULE = {
    PyModuleDef_HEAD_INIT,
    "wayland_backend",
    NULL,
    -1,
    EXPOSED_METHODS
};

PyMODINIT_FUNC PyInit_wayland_backend(void)
{
    PyObject *mod = PyModule_Create(&WAYLAND_BACKEND_MODULE);

    return mod;
}
