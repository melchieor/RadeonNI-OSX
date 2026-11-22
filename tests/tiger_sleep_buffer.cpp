#include <cassert>
#include <cstring>
#include "../kext/RadeonNI/RadeonNITigerSleepBuffer.h"
int mock_create_fail,mock_prepare_fail,mock_complete_fail,mock_segment_fail;
int mock_prepares,mock_completes,mock_releases;uint32_t mock_mapped_base;
int mock_operation_fail,mock_operation_calls;uint32_t mock_last_operation;
int rdn_tiger_sleep_stage_matches(void *p,rdn_stage *stage,rdn_gart *gart)
{rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;return s && &s->stage==stage && s->gart==gart && s->memory && s->prepared && stage->phase==RDN_STAGE_BOUND;}
int main()
{
 rdn_tiger_sleep_stage stage={};rdn_gart gart={true};rdn_accel accel={};
 rdn_tiger_sleep_buffer buffer={&stage,&accel};uint32_t words[]={0x01234567,0x89abcdef};
 stage.memory=IOBufferMemoryDescriptor::withOptions(0,4096,4096);stage.prepared=true;
 stage.gart=&gart;stage.stage.phase=RDN_STAGE_BOUND;stage.stage.bytes=4096;stage.size=4096;
 accel.swapped=true;assert(!rdn_tiger_sleep_write_ib(&buffer,words,2));
 uint32_t *p=(uint32_t *)stage.memory->getBytesNoCopy();assert(p[0]==words[0] && p[1]==words[1]);
 memset(p+2,0,4096-2*sizeof(*p));
 assert(rdn_tiger_sleep_write_ib(&buffer,words,1025));assert(!rdn_tiger_sleep_cpu_barrier(0));
 assert(!rdn_tiger_sleep_publish_ib(&buffer) && mock_last_operation==kIOMemoryIncoherentIOStore);
 assert(!rdn_tiger_sleep_sync_data(&stage) && mock_last_operation==kIOMemoryIncoherentIOFlush);
 mock_operation_fail=1;assert(rdn_tiger_sleep_publish_ib(&buffer) && rdn_tiger_sleep_sync_data(&stage));
 mock_operation_fail=0;stage.prepared=false;assert(rdn_tiger_sleep_publish_ib(&buffer));stage.prepared=true;
 rdn_quiesce q={};rdn_sleep_copy copy={};rdn_sleep_runtime runtime={};unsigned char result[4096];
 q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=4;q.internal_hold=1;
 copy.stage=&stage.stage;copy.quiesce=&q;copy.generation=4;copy.transfer.phase=RDN_TRANSFER_READY;copy.transfer.fence=0;
 runtime.stage=&stage.stage;runtime.copy=&copy;runtime.quiesce=&q;runtime.use_gart_ib=1;runtime.submitted=1;runtime.saw_fence=1;runtime.coherency_verified=1;
 memset(result,0,sizeof(result));assert(!rdn_tiger_sleep_copy_bytes(&stage,&copy,&runtime,result,sizeof(result)));
 assert(!memcmp(result,p,4096));assert(rdn_tiger_sleep_copy_bytes(&stage,&copy,&runtime,p,4096));
 runtime.coherency_verified=0;assert(rdn_tiger_sleep_copy_bytes(&stage,&copy,&runtime,result,sizeof(result)));
 runtime.coherency_verified=1;q.internal_hold=0;assert(rdn_tiger_sleep_copy_bytes(&stage,&copy,&runtime,result,sizeof(result)));
 stage.memory->release();return 0;
}
