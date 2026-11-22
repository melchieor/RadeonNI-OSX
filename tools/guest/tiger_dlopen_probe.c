/* Test loading one user-space bundle without invoking its driver entry points. */
#include <Python/Python.h>
#include <dlfcn.h>

static PyObject *probe(PyObject *self, PyObject *args)
{
 const char *path, *name, *err;
 void *handle, *symbol;
 (void)self;
 if (!PyArg_ParseTuple(args,"ss",&path,&name)) return NULL;
 dlerror();
 handle=dlopen(path,RTLD_NOW|RTLD_LOCAL);
 if (!handle) {
  err=dlerror(); PyErr_SetString(PyExc_RuntimeError,err?err:"dlopen failed");return NULL;
 }
 dlerror();
 symbol=dlsym(handle,name);
 err=dlerror();
 if (err || !symbol) {
  PyErr_SetString(PyExc_RuntimeError,err?err:"missing export");dlclose(handle);return NULL;
 }
 /* Process exit reclaims the handle; avoid adding an unload test here. */
 Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef methods[]={{"probe",probe,METH_VARARGS,"Load one bundle and look up an export."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_dlopen_probe(void) { Py_InitModule("rdn_dlopen_probe",methods); }
