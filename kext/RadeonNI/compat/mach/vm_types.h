/* SPDX-License-Identifier: MIT */
#ifndef RDN_COMPAT_MACH_VM_TYPES_H
#define RDN_COMPAT_MACH_VM_TYPES_H

#if defined(RDN_SDK_VM_MAP_FIX)
/* The exported 10.5 SDK omits the private kernel vm_map_t typedef.
 * Keep its port-based spelling out of kernel C++ method mangling; Leopard's
 * actual kernel exports the methods with struct _vm_map pointer arguments.
 * This opt-in overlay is not used for builds with native kernel headers.
 */
#define vm_map_t rdn_sdk_port_vm_map_t
#include_next <mach/vm_types.h>
#undef vm_map_t
struct _vm_map;
typedef struct _vm_map *vm_map_t;
#else
#include_next <mach/vm_types.h>
#endif

#endif
