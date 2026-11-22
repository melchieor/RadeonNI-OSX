/*
 * Kernel module descriptor. Xcode generates this file for kext targets; the
 * kext is built with a plain Makefile, so it is written out here.
 *
 * Copyright (c) 2026 kouta-kun and Claude
 * SPDX-License-Identifier: MIT
 */

#include <mach/mach_types.h>

#if RDN_NATIVE_KMOD_RUNTIME
/* The Tiger compatibility kernel exports __start.  Keep our callbacks
 * local and name them independently so kld never sees a duplicate export. */
static kern_return_t rdn_kmod_start(kmod_info_t *ki, void *data);
static kern_return_t rdn_kmod_stop(kmod_info_t *ki, void *data);
KMOD_EXPLICIT_DECL(org.osxgpu.driver.RadeonNI, "0.1.0", rdn_kmod_start, rdn_kmod_stop)
#else
extern kern_return_t _start(kmod_info_t *ki, void *data);
extern kern_return_t _stop(kmod_info_t *ki, void *data);
KMOD_EXPLICIT_DECL(org.osxgpu.driver.RadeonNI, "0.1.0", _start, _stop)
#endif

/* An IOKit driver has no module start/stop routines of its own. */
__attribute__((visibility("hidden"))) kmod_start_func_t *_realmain = 0;
__attribute__((visibility("hidden"))) kmod_stop_func_t *_antimain = 0;
__attribute__((visibility("hidden"))) int _kext_apple_cc = __APPLE_CC__;

#if RDN_NATIVE_KMOD_RUNTIME
/* Host cross-builds cannot use the SDK's old long-branch startup archive.
 * This driver has no custom start/stop callbacks: delegate initialization
 * and finalization of its C++ objects to the actual kernel runtime.
 * Reject callback additions rather than silently ignoring them.
 */
extern kern_return_t OSRuntimeInitializeCPP(kmod_info_t *info);
extern kern_return_t OSRuntimeFinalizeCPP(kmod_info_t *info);

static kern_return_t rdn_kmod_start(kmod_info_t *info, void *data)
{
    (void)data;
    if (_realmain || _antimain)
        return KERN_FAILURE;
    return OSRuntimeInitializeCPP(info);
}

static kern_return_t rdn_kmod_stop(kmod_info_t *info, void *data)
{
    (void)data;
    if (_realmain || _antimain)
        return KERN_FAILURE;
    return OSRuntimeFinalizeCPP(info);
}
#endif
