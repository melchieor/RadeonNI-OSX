/* SPDX-License-Identifier: MIT
 * Host-only logic test for the optional constructor/destructor bridge.
 * The mocked calls do not establish kernel loadability or C++ kernel ABI.
 */
#include <assert.h>
#include <stdio.h>
#include <mach/mach_types.h>

extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
extern kmod_start_func_t *_realmain;
extern kmod_stop_func_t *_antimain;
static kmod_info_t info;
static unsigned starts, stops;
static kern_return_t init_result, fini_result;

kern_return_t OSRuntimeInitializeCPP(kmod_info_t *value)
{
    assert(value == &info);
    ++starts;
    return init_result;
}

kern_return_t OSRuntimeFinalizeCPP(kmod_info_t *value)
{
    assert(value == &info);
    ++stops;
    return fini_result;
}

static kern_return_t unexpected_callback(kmod_info_t *value, void *data)
{
    (void)value;
    (void)data;
    assert(!"custom callback must be rejected");
    return KERN_FAILURE;
}

int main(void)
{
    init_result = KERN_SUCCESS;
    assert(_start(&info, 0) == KERN_SUCCESS && starts == 1 && stops == 0);
    init_result = KERN_RESOURCE_SHORTAGE;
    assert(_start(&info, 0) == KERN_RESOURCE_SHORTAGE && starts == 2);
    fini_result = KERN_SUCCESS;
    assert(_stop(&info, 0) == KERN_SUCCESS && stops == 1);
    fini_result = KERN_FAILURE;
    assert(_stop(&info, 0) == KERN_FAILURE && stops == 2);
    _realmain = unexpected_callback;
    assert(_start(&info, 0) == KERN_FAILURE && starts == 2);
    assert(_stop(&info, 0) == KERN_FAILURE && stops == 2);
    _realmain = 0;
    _antimain = unexpected_callback;
    assert(_start(&info, 0) == KERN_FAILURE && starts == 2);
    assert(_stop(&info, 0) == KERN_FAILURE && stops == 2);
    puts("PASS kernel runtime bridge forwarding, errors and unsupported callback rejection (host mocks)");
    return 0;
}
