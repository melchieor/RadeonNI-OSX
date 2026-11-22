/* Explicit power-retained graphics rehearsal. Never requests system sleep. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include "rdn_user.h"
#include "rdn_probe_device.h"
typedef char report_is_23_words[sizeof(struct rdn_user_sleep_rehearsal)==23*4?1:-1];
#ifdef RDN_MAINTENANCE_PROBE
#ifdef RDN_RESOURCE_PROBE
static struct rdn_user_sleep_resource resource;
static uint32_t probe_offset;
#define maintenance resource.maintenance
typedef char resource_is_56_words[sizeof(resource)==56*4?1:-1];
#else
static struct rdn_user_sleep_maintenance maintenance;
#endif
typedef char maintenance_is_32_words[sizeof(maintenance)==32*4?1:-1];
#endif
static void show(const struct rdn_user_sleep_rehearsal *r)
{
 printf("version=%u enabled=%u state=%u result=%u generation=%u elapsed_ms=%u timeout_ms=%u\n",r->version,r->enabled,r->state,r->result,r->generation,r->elapsed_ms,r->timeout_ms);
 printf("sleep_supported=%u power_retained=%u full_mmio_gated=%u resources_recreated=%u\n",r->sleep_supported,r->power_retained,r->full_mmio_gated,r->resources_recreated);
 printf("held_witness=%u gate_verified=%u queue_state_unchanged=%u fan_full_requested=%u busy_mask=0x%x\n",r->held_witness,r->gate_verified,r->queue_state_unchanged,r->fan_full_requested,r->busy_mask);
 printf("fence=%u/%u write_ptr=%u/%u read_ptr=%u/%u\n",r->fence_before,r->fence_after,r->wptr_before,r->wptr_after,r->rptr_before,r->rptr_after);
}
static kern_return_t request(io_connect_t c,unsigned action,struct rdn_user_sleep_rehearsal *r)
{
 IOByteCount bytes=sizeof(*r);memset(r,0,sizeof(*r));
#ifdef RDN_MAINTENANCE_PROBE
 bytes=sizeof(maintenance);memset(&maintenance,0,sizeof(maintenance));
#ifdef RDN_RESOURCE_PROBE
 bytes=sizeof(resource);memset(&resource,0,sizeof(resource));
 kern_return_t e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_RESOURCE,4,&bytes,action,action?50:0,action?probe_offset:0,action?4096:0,&resource);
 if(!e && (bytes!=sizeof(resource) || resource.version!=RDN_SLEEP_RESOURCE_VERSION || resource.size!=sizeof(resource)))return kIOReturnBadArgument;
 if(!e)printf("resource_version=%u inventory_valid=%u allocation_valid=%u private_connection=%u saved_words=%u restored_words=%u poison_mismatches=%u restore_mismatches=%u metadata_unchanged=%u coverage_complete=%u device_restored=%u\n",resource.version,resource.inventory_valid,resource.allocation_valid,resource.private_connection,resource.saved_words,resource.restored_words,resource.poison_mismatches,resource.restore_mismatches,resource.metadata_unchanged,resource.coverage_complete,resource.device_restored);
 if(!e)printf("visible_allocations=%u visible_used=%u command_allocations=%u command_used=%u hidden_allocations=%u hidden_used=%u reserved_bytes=%u gart_bindings=%u topology=%08x/%08x\n",resource.visible_allocations,resource.visible_used,resource.command_allocations,resource.command_used,resource.hidden_allocations,resource.hidden_used,resource.reserved_bytes,resource.gart_bindings,resource.topology_before,resource.topology_after);
 bytes=sizeof(maintenance);
#else
 kern_return_t e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_MAINTENANCE,2,&bytes,action,action?50:0,&maintenance);
#endif
 if(!e && (bytes!=sizeof(maintenance) || maintenance.version!=RDN_SLEEP_MAINTENANCE_VERSION || maintenance.size!=sizeof(maintenance)))return kIOReturnBadArgument;
 *r=maintenance.base;bytes=sizeof(*r);
 if(!e)printf("maintenance_version=%u cursor_excluded=%u cursor_resumed=%u fan_excluded=%u hotplug_excluded=%u telemetry_excluded=%u hold_ms=%u cursor_deferred=%u\n",maintenance.version,maintenance.cursor_excluded,maintenance.cursor_resumed,maintenance.fan_excluded,maintenance.hotplug_excluded,maintenance.telemetry_excluded,maintenance.hold_ms,maintenance.cursor_deferred);
#else
 kern_return_t e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_REHEARSAL,2,&bytes,action,action?50:0,r);
#endif
 if(!e && (bytes!=sizeof(*r) || r->version!=RDN_SLEEP_REHEARSAL_VERSION || r->size!=sizeof(*r)))return kIOReturnBadArgument;
 return e;
}
int main(int argc,char **argv)
{
 int run=argc==2&&!strcmp(argv[1],"--rehearse");
 if(argc>2 || (argc==2&&!run&&strcmp(argv[1],"--status"))) {
  fprintf(stderr,"usage: this-probe --status | sudo this-probe --rehearse\n");return 2;
 }
 if(run && geteuid()!=0){fprintf(stderr,"Rehearsal requires sudo; status is read-only.\n");return 2;}
 io_service_t service=rdn_probe_device("6704");io_connect_t c=0;
 if(!service){fprintf(stderr,"V7900 accelerator not found\n");return 1;}
 kern_return_t e=IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&c);
 IOObjectRelease(service);if(e){fprintf(stderr,"Open failed 0x%x\n",e);return 1;}
 struct rdn_user_sleep_rehearsal r;int status=1;unsigned offset=0,allocated=0;
 vm_address_t address=0;vm_size_t length=0;int mapped=0;
 e=request(c,RDN_SLEEP_STATUS,&r);
 if(e){fprintf(stderr,"Status failed 0x%x; this kernel may lack the new API. No rehearsal attempted.\n",e);goto done;}
 show(&r);if(!run){status=0;goto done;}
#ifdef RDN_RESOURCE_PROBE
 if(!resource.inventory_valid){fprintf(stderr,"Inventory invalid; refusing resource rehearsal\n");goto done;}
#endif
 if(!r.enabled || r.state || r.sleep_supported){fprintf(stderr,"Unexpected prerequisites; refusing rehearsal\n");goto done;}
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_ALLOC,2,1,4096,4096,&offset);
 if(e){fprintf(stderr,"Sentinel allocation failed 0x%x\n",e);goto done;}allocated=1;
#ifdef RDN_RESOURCE_PROBE
 probe_offset=offset;
#endif
 e=IOConnectMapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),&address,&length,kIOMapAnywhere);
 if(e){fprintf(stderr,"Sentinel mapping failed 0x%x\n",e);goto done;}mapped=1;
 if((uint64_t)offset+4096>length){fprintf(stderr,"Sentinel outside mapped aperture\n");goto done;}
 volatile uint32_t *words=(volatile uint32_t *)(address+offset);
 for(unsigned i=0;i<1024;i++)words[i]=0xa52c0000u^i;
 __sync_synchronize();
#ifdef RDN_INDEX_PROBE
 /* A single owned page holds both the command and the source/destination.
    The GPU copies 16 bytes within it; the kernel compares the destination
    through the register window and the CPU aperture after draining the GPU. */
 struct rdn_user_info info;IOByteCount info_bytes=sizeof(info);
 unsigned fence=0,reached=0;uint64_t gpu_base;
 memset(&info,0,sizeof(info));
 e=IOConnectMethodScalarIStructureO(c,RDN_UC_GET_INFO,0,&info_bytes,&info);
 if(e || info_bytes!=sizeof(info) || info.pci_device_id!=0x6704) {
  fprintf(stderr,"GPU information check failed 0x%x\n",e);goto done;
 }
 gpu_base=((uint64_t)info.vram_gpu_base_hi<<32)|info.vram_gpu_base_lo;
 uint64_t src=gpu_base+offset+1024,dst=gpu_base+offset;
 volatile uint32_t *ib=words+64;
 ib[0]=0xc0044100;ib[1]=(uint32_t)src;ib[2]=(uint32_t)(src>>32)|0x80000000u;
 ib[3]=(uint32_t)dst;ib[4]=(uint32_t)(dst>>32);ib[5]=16;
 for(unsigned i=6;i<16;i++)ib[i]=0x80000000u;
 __sync_synchronize();
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_SUBMIT,2,1,offset+256,16,&fence);
 if(e){fprintf(stderr,"GPU submission failed 0x%x; stop\n",e);goto done;}
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_FENCE_WAIT,2,1,fence,2000,&reached);
 if(e || !reached){fprintf(stderr,"GPU completion uncertain 0x%x; stop and restart before further tests\n",e);goto done;}
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_SYNC_FOR_CPU,0,0);
 if(e){fprintf(stderr,"GPU synchronization failed 0x%x\n",e);goto done;}
 __sync_synchronize();
 for(unsigned i=0;i<4;i++)if(words[i]!=(0xa52c0000u^(256+i))) {
  fprintf(stderr,"GPU copy comparison failed at word %u\n",i);goto done;
 }
 /* Preserve the existing probe's whole-page expected pattern. */
 for(unsigned i=0;i<4;i++)words[256+i]=0xa52c0000u^i;
 __sync_synchronize();
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_SUBMIT,2,1,offset+256,16,&fence);
 if(e){fprintf(stderr,"Second GPU submission failed 0x%x\n",e);goto done;}
 reached=0;
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_FENCE_WAIT,2,1,fence,2000,&reached);
 if(e || !reached){fprintf(stderr,"Second GPU completion uncertain 0x%x; stop and restart\n",e);goto done;}
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_SYNC_FOR_CPU,0,0);
 if(e)goto done;
 /* The source and command can now be restored without touching destination. */
 for(unsigned i=64;i<80;i++)words[i]=0xa52c0000u^i;
 for(unsigned i=256;i<260;i++)words[i]=0xa52c0000u^i;
 __sync_synchronize();
 puts("GPU wrote the 16-byte private sentinel; kernel indexed comparison follows.");
#endif
#ifdef RDN_RESOURCE_PROBE
 puts("Saving, inverting, and restoring ONLY this connection's new private 4 KiB sentinel.");
#endif
 puts("Rehearsing ONCE with power retained; fan may run at maximum then ease down. No sleep request.");
 e=request(c,RDN_SLEEP_REHEARSE,&r);
 if(e){fprintf(stderr,"Rehearsal request failed 0x%x%s; stop and share output.\n",e,
   e==kIOReturnBadArgument?" (bad argument or private-buffer admission rejection)":
   e==kIOReturnBusy?" (busy)":e==kIOReturnUnsupported?" (unsupported)":"");goto done;}
 show(&r);
 e=IOConnectMethodScalarIScalarO(c,RDN_UC_SYNC_FOR_CPU,0,0);
 if(e){fprintf(stderr,"Sentinel synchronization failed 0x%x\n",e);goto done;}
 __sync_synchronize();unsigned errors=0;
 for(unsigned i=0;i<1024;i++)if(words[i]!=(0xa52c0000u^i))++errors;
 printf("Owned VRAM sentinel: %u mismatched words of 1024\n",errors);
 status=r.result || r.state || !r.held_witness || !r.gate_verified || !r.queue_state_unchanged ||
        r.sleep_supported || !r.power_retained || r.full_mmio_gated || r.resources_recreated || errors;
#ifdef RDN_MAINTENANCE_PROBE
 status=status || !maintenance.cursor_excluded || !maintenance.cursor_resumed ||
        !maintenance.fan_excluded || !maintenance.hotplug_excluded || !maintenance.telemetry_excluded || maintenance.hold_ms<20;
#endif
#ifdef RDN_RESOURCE_PROBE
 status=status || !resource.inventory_valid || !resource.allocation_valid || !resource.private_connection ||
        resource.saved_words!=1024 || resource.restored_words!=1024 || resource.restore_mismatches ||
        resource.poison_mismatches || !resource.metadata_unchanged || resource.coverage_complete || resource.device_restored;
#endif
 puts(status?"Rehearsal incomplete/failed: keep sleep blocked and share output.":
             "Power-retained rehearsal passed; actual system sleep remains unsupported.");
done:
 if(mapped)IOConnectUnmapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),address);
 if(allocated)IOConnectMethodScalarIScalarO(c,RDN_UC_FREE,1,0,offset);
 IOServiceClose(c);return status;
}
