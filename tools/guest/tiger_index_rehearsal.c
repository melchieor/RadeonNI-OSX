/* Tiger Python 2.3 wrapper of the existing power-retained resource probe. */
#include <Python/Python.h>
#define RDN_MAINTENANCE_PROBE 1
#define RDN_RESOURCE_PROBE 1
#define RDN_INDEX_PROBE 1
#define main rdn_resource_probe_main
#include "sleep-rehearsal.c"
#undef main
static PyObject *rehearse(PyObject *self, PyObject *args)
{
    char *argv[] = {"resource-rehearsal", "--rehearse", 0};
    int result;
    (void)self;
    if (!PyArg_ParseTuple(args, "")) return NULL;
    result = rdn_resource_probe_main(2, argv);
    fflush(stdout); fflush(stderr);
    if (result) { PyErr_SetString(PyExc_RuntimeError, "Rehearsal failed or incomplete; stop and share output"); return NULL; }
    Py_INCREF(Py_None);
    return Py_None;
}
static PyMethodDef methods[]={{"rehearse",rehearse,METH_VARARGS,"Run one powered resource rehearsal."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_index_rehearsal(void) { Py_InitModule("rdn_index_rehearsal", methods); }
