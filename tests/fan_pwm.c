/* Mock MMIO checks for the build-specific PWM floor. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "rdn_pm.h"
static uint32_t control0=0x01815e87,scale=135,control2=0x00cd0c00;
static unsigned writes,drop;
static uint32_t rd(void *cookie,uint32_t reg)
{ (void)cookie;return reg==0x76c?control0:reg==0x770?scale:reg==0x774?control2:0; }
static void wr(void *cookie,uint32_t reg,uint32_t value)
{ (void)cookie;++writes;if(drop){drop=0;return;}if(reg==0x76c)control0=value;if(reg==0x774)control2=value; }
int main(void)
{
 struct rdn_os os;struct rdn_card card;unsigned before;
 memset(&os,0,sizeof(os));memset(&card,0,sizeof(card));
 os.mmio_read32=rd;os.mmio_write32=wr;card.os=&os;card.family=RDN_FAMILY_CAYMAN;
#if defined(RDN_LEOPARD_FAN) || defined(RDN_TIGER_FAN)
 assert(!rdn_pm_fan_percent(&card,40));assert((control0&255)==54);
 before=writes;assert(rdn_pm_fan_percent(&card,39)<0 && writes==before);
#else
 before=writes;assert(rdn_pm_fan_percent(&card,50)<0 && writes==before);
 assert(!rdn_pm_fan_percent(&card,60));assert((control0&255)==81);
#endif
 before=writes;assert(rdn_pm_fan_percent(&card,101)<0 && writes==before);
 assert(!rdn_pm_fan_full(&card));assert((control0&255)==135);
 scale=0;before=writes;assert(rdn_pm_fan_full(&card)<0 && writes==before);scale=135;
 control0=0x01815e51;control2=0x00cd1437;drop=1;
 assert(rdn_pm_fan_full(&card)<0 && control0==0x01815e51 && control2==0x00cd1437);
 card.family=RDN_FAMILY_TURKS;before=writes;assert(rdn_pm_fan_full(&card)<0 && writes==before);
 puts("fan PWM: calibrated duty, floor, upper bound, full speed, readback rollback and ASIC guard passed");
 return 0;
}
