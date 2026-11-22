/* Tiger Python extension: only the powered sleep-resource status request. */
#include <Python/Python.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include "rdn_user.h"
#include "rdn_probe_device.h"

static PyObject *status(PyObject *self, PyObject *args)
{
    io_service_t service;
    io_connect_t connection = 0;
    IOByteCount bytes;
    kern_return_t error;
    struct rdn_user_sleep_resource r;
    (void)self;
    if (!PyArg_ParseTuple(args, "")) return NULL;
    service = rdn_probe_device("6704");
    if (!service) { PyErr_SetString(PyExc_RuntimeError, "Unique V7900 accelerator not found"); return NULL; }
    error = IOServiceOpen(service, mach_task_self(), RDN_UC_TYPE_V2, &connection);
    IOObjectRelease(service);
    if (error) { PyErr_Format(PyExc_RuntimeError, "Accelerator open failed: 0x%x", error); return NULL; }
    memset(&r, 0, sizeof(r));
    bytes = sizeof(r);
    error = IOConnectMethodScalarIStructureO(connection, RDN_UC_SLEEP_RESOURCE, 4,
            &bytes, RDN_SLEEP_STATUS, 0, 0, 0, &r);
    IOServiceClose(connection);
    if (error) { PyErr_Format(PyExc_RuntimeError, "Resource status failed: 0x%x", error); return NULL; }
    if (bytes != sizeof(r) || r.version != RDN_SLEEP_RESOURCE_VERSION || r.size != sizeof(r)) {
        PyErr_SetString(PyExc_RuntimeError, "Unexpected resource status version or size"); return NULL;
    }
    printf("resource_version=%u inventory_valid=%u visible_allocations=%u visible_used=%u command_allocations=%u command_used=%u hidden_allocations=%u hidden_used=%u reserved_bytes=%u gart_bindings=%u topology=%08x\n",
        r.version, r.inventory_valid, r.visible_allocations, r.visible_used,
        r.command_allocations, r.command_used, r.hidden_allocations, r.hidden_used,
        r.reserved_bytes, r.gart_bindings, r.topology_after);
    printf("enabled=%u state=%u result=%u generation=%u sleep_supported=%u power_retained=%u full_mmio_gated=%u resources_recreated=%u coverage_complete=%u device_restored=%u\n",
        r.maintenance.base.enabled, r.maintenance.base.state, r.maintenance.base.result,
        r.maintenance.base.generation, r.maintenance.base.sleep_supported,
        r.maintenance.base.power_retained, r.maintenance.base.full_mmio_gated,
        r.maintenance.base.resources_recreated, r.coverage_complete, r.device_restored);
    fflush(stdout);
    Py_INCREF(Py_None);
    return Py_None;
}
static PyMethodDef methods[]={{"status", status, METH_VARARGS, "Read powered resource status."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_sleepstatus(void) { Py_InitModule("rdn_sleepstatus", methods); }
