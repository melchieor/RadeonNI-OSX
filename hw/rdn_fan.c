/* Conservative temperature-only V7900 fan policy. SPDX-License-Identifier: MIT */
#include "rdn_fan.h"

void rdn_fan_init(struct rdn_fan_policy *p)
{
 p->last_poll=0; p->last_reduction=0; p->percent=100;
 p->good_samples=0; p->reason=RDN_FAN_WARMUP;
}
unsigned rdn_fan_update(struct rdn_fan_policy *p, uint64_t now,
                       int temp, int valid, unsigned rpm,
                       unsigned minimum, int tach_valid, unsigned fault)
{
 unsigned reason=fault, target=100;
 if(!valid || temp<10000 || temp>110000)reason|=RDN_FAN_BAD_TEMP;
 if(!tach_valid || rpm<(minimum>500?minimum:500) || rpm>30000)reason|=RDN_FAN_BAD_TACH;
 if(p->good_samples && (now<=p->last_poll || now-p->last_poll>2000))reason|=RDN_FAN_LATE;
 p->last_poll=now;
 if(reason) {
  p->good_samples=0; p->percent=100; p->last_reduction=now; p->reason=reason;
  return 100;
 }
 if(p->good_samples<8)++p->good_samples;
 if(p->good_samples<8) {
  p->reason=RDN_FAN_WARMUP; p->last_reduction=now;
  return p->percent=100;
 }
 /* Controlled 40% floor below 50 C. Rejoin the established curve at
    55 C / 65%; temperatures at/above 55 C retain the previous cooling. */
 target=temp<=50000?40:temp>=80000?100:
        temp<55000?40+(unsigned)((temp-50000)*5+999)/1000:
        temp<70000?60+(unsigned)(temp-50000+999)/1000:
                   80+(unsigned)(temp-70000+499)/500;
 if(target<p->percent) {
  if(now-p->last_reduction<1000)target=p->percent;
  else {
   if(p->percent-target>2)target=p->percent-2;
   p->last_reduction=now;
  }
 }
 p->reason=0;
 return p->percent=target;
}
