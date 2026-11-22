/* Tiger Python 2.3 adapter for the existing CGL renderer diagnostic. */
#include <Python/Python.h>
#define main rdn_glprobe_main
#include "glprobe.c"
#undef main

static PyObject *probe(PyObject *self, PyObject *args)
{
 int draw_mode=0, result;
 char *argv[3]={"glprobe", "draw", 0};
 (void)self;
 if(!PyArg_ParseTuple(args,"|i",&draw_mode))return NULL;
 result=rdn_glprobe_main(draw_mode?2:1,argv);
 fflush(stdout);
 return PyInt_FromLong(result);
}
static PyMethodDef methods[]={{"probe",probe,METH_VARARGS,"List CGL renderers or exercise one offscreen."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_glprobe(void) {Py_InitModule("rdn_glprobe",methods);}
