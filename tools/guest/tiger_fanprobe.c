/* Tiger Python 2.3 extension wrapping the read-only fan monitor. */
#include <Python/Python.h>
#define main rdn_monitor_main
#include "fanmonitor.c"
#undef main

static PyObject *sample(PyObject *self, PyObject *args)
{
 int count=10, result;
 char text[16];
 char *argv[3] = {"fan-monitor", text, 0};
 (void)self;
 if (!PyArg_ParseTuple(args,"|i",&count)) return NULL;
 if (count < 1 || count > 120) {
  PyErr_SetString(PyExc_ValueError,"sample count must be between 1 and 120");
  return NULL;
 }
 snprintf(text,sizeof(text),"%d",count);
 result=rdn_monitor_main(2,argv);
 if (result) {PyErr_SetString(PyExc_RuntimeError,"fan telemetry failed");return NULL;}
 Py_INCREF(Py_None);
 return Py_None;
}

static PyMethodDef methods[]={{"sample",sample,METH_VARARGS,"Read temperature and fan telemetry."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_fanprobe(void) { Py_InitModule("rdn_fanprobe",methods); }
