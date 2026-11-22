/* Mock Cayman cursor register and high-VRAM address checks. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "rdn_card.h"
#include "rdn_cursor.h"
#include "rdn_reg.h"
static uint32_t regs[0x20000/4];static unsigned writes,head;
static uint32_t rd(void *cookie,uint32_t reg)
{(void)cookie;return reg==MC_VM_FB_LOCATION?0xf800:regs[reg/4];}
static void wr(void *cookie,uint32_t reg,uint32_t value)
{
 (void)cookie;unsigned local=reg-rdn_crtc_offset(head);
 assert(local==0x6998 || local==0x699c || local==0x69a0 || local==0x69a4 ||
        local==0x69a8 || local==0x69ac || local==0x69c8);
 assert(reg<sizeof(regs));++writes;regs[reg/4]=value;
}
int main(void)
{
 struct rdn_os os={0};struct rdn_card card={0};
 os.mmio_read32=rd;os.mmio_write32=wr;card.os=&os;card.family=RDN_FAMILY_CAYMAN;
 for(head=0;head<6;head++) {
  unsigned off=rdn_crtc_offset(head);memset(regs,0,sizeof(regs));card.display_crtc=head;
  rdn_cursor_set(&card,31u<<20,12,20,true);
  assert(regs[(off+0x699c)/4]==31u<<20 && regs[(off+0x69a4)/4]==0xf8);
  assert(regs[(off+0x69a8)/4]==((12u<<16)|20));
  assert(regs[(off+0x69a0)/4]==((63u<<16)|63));
  assert(regs[(off+0x6998)/4]&1);assert(!(regs[(off+0x69c8)/4]&(1u<<16)));
  rdn_cursor_set(&card,31u<<20,-12,-8,true);
  assert(!regs[(off+0x69a8)/4] && regs[(off+0x69ac)/4]==((12u<<16)|8));
  rdn_cursor_set(&card,31u<<20,-100,-100,true);
  assert(regs[(off+0x69ac)/4]==((63u<<16)|63));
  rdn_cursor_set(&card,31u<<20,0,0,false);assert(!(regs[(off+0x6998)/4]&1));
 }
 unsigned before=writes;card.display_crtc=6;rdn_cursor_set(&card,0,0,0,true);assert(writes==before);
 assert((31u<<20)+64u*64u*4u < (32u<<20));
 puts("cursor model: six CRTC banks, high VRAM address, size, clipping, hide, unlock and reserved range passed");
 return 0;
}
