/* Temperature-only V7900 fan policy. SPDX-License-Identifier: MIT */
#ifndef RDN_FAN_H
#define RDN_FAN_H
#include <stdint.h>
enum {
 RDN_FAN_BAD_TEMP=1, RDN_FAN_BAD_TACH=2, RDN_FAN_LATE=4,
 RDN_FAN_DEVICE_FAULT=8, RDN_FAN_WRITE_FAULT=16, RDN_FAN_WARMUP=32
};
struct rdn_fan_policy {
 uint64_t last_poll, last_reduction;
 unsigned percent, good_samples, reason;
};
/* Pure policy: no MMIO, clock, voltage, firmware or SMC operations. */
void rdn_fan_init(struct rdn_fan_policy *);
unsigned rdn_fan_update(struct rdn_fan_policy *, uint64_t now_ms,
                       int temperature_millic, int temperature_valid,
                       unsigned rpm, unsigned minimum_rpm, int tach_valid,
                       unsigned external_fault);
#endif
