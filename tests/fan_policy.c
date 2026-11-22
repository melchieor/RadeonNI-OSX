/* Host-only fan policy tests; no hardware access. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include "rdn_fan.h"

static void cool(struct rdn_fan_policy *p, uint64_t *now)
{
 unsigned i;rdn_fan_init(p);
 for(i=0;i<80;i++){*now+=500;rdn_fan_update(p,*now,40000,1,3000,1000,1,0);}
 assert(p->percent==40 && !p->reason);
}
int main(void)
{
 struct rdn_fan_policy p;uint64_t now=0;unsigned i,duty;
 rdn_fan_init(&p);assert(p.percent==100);
 for(i=0;i<7;i++){now+=500;assert(rdn_fan_update(&p,now,40000,1,3000,1000,1,0)==100);}
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,75000,1,3000,1000,1,0)==90);
 now+=500;assert(rdn_fan_update(&p,now,80000,1,3000,1000,1,0)==100);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,40000,0,3000,1000,1,0)==100);
 assert(p.reason&RDN_FAN_BAD_TEMP);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,40000,1,0,1000,1,0)==100);
 assert(p.reason&RDN_FAN_BAD_TACH);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,40000,1,3000,1000,0,0)==100);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,40000,1,900,1000,1,0)==100);
 cool(&p,&now);
 now+=2500;assert(rdn_fan_update(&p,now,40000,1,3000,1000,1,0)==100);
 assert(p.reason&RDN_FAN_LATE);
 cool(&p,&now);
 assert(rdn_fan_update(&p,now-1,40000,1,3000,1000,1,0)==100);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,40000,1,3000,1000,1,RDN_FAN_WRITE_FAULT)==100);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,0,1,3000,1000,1,0)==100);
 cool(&p,&now);
 now+=500;assert(rdn_fan_update(&p,now,120000,1,3000,1000,1,0)==100);
 /* Confirm the quiet curve joins continuously, and all cooling requests
    at/above 55 C match the previous 60%-minimum policy. */
 for(i=100;i<=160;i++) {
  int temp=(int)i*500;
  unsigned expected=temp<=50000?40:temp<55000?40+(unsigned)((temp-50000)*5+999)/1000:
                    temp<70000?60+(unsigned)(temp-50000+999)/1000:
                    temp<80000?80+(unsigned)(temp-70000+499)/500:100;
  cool(&p,&now);now+=500;
  assert(rdn_fan_update(&p,now,temp,1,3000,1000,1,0)==expected);
 }
 /* Exercise every half-degree sample over the accepted range. */
 for(i=0;i<=240;i++) {
  int temp=(int)i*500;unsigned j,previous;
  cool(&p,&now);
  for(j=0;j<100;j++) {
   previous=p.percent;now+=500;
   duty=rdn_fan_update(&p,now,temp,1,3000,1000,1,0);
   assert(duty>=40 && duty<=100);
   if(temp<10000 || temp>=80000)assert(duty==100);
   if(duty<previous)assert(previous-duty<=2);
  }
 }
 puts("fan policy: warmup, ramp, temperature/tach faults, late polling and 24,100 curve samples passed");
 return 0;
}
