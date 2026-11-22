/* Runs the real image-storage regression against ordinary process memory on Tiger. */
#include <Python/Python.h>
#define main rdn_live_image_regression_main
#include "../../tests/live_image.c"
#undef main
static PyObject *check(PyObject *self,PyObject *args)
{
 (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
 if(rdn_live_image_regression_main()){PyErr_SetString(PyExc_RuntimeError,"image regression failed");return NULL;}
 puts("LIVE_IMAGE_TIGER_PASS: chunked capture, stale plan, integrity and failure cleanup checks.");fflush(stdout);
 Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef methods[]={{"check",check,METH_VARARGS,"Run image-storage regression."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_live_image_test(void){Py_InitModule("rdn_live_image_test",methods);}
