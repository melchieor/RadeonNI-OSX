#include <cassert>
#include <cstring>
#include "../kext/RadeonNI/RadeonNITigerSleepStage.h"
int mock_create_fail,mock_prepare_fail,mock_complete_fail,mock_segment_fail;
int mock_prepares,mock_completes,mock_releases,flush_fail,sets,clears;
int mock_operation_fail,mock_operation_calls;uint32_t mock_last_operation;
uint32_t mock_mapped_base=0x30000000,last_mapped_address;
extern "C" int rdn_mem_alloc(rdn_mem *m,uint64_t,uint64_t,uint64_t *p){if(m->used>=2)return -1;*p=4096*++m->used;return 0;}
extern "C" void rdn_mem_free(rdn_mem *m,uint64_t){assert(m->used>0);--m->used;}
extern "C" void rdn_gart_set_page(rdn_gart *,uint32_t,uint64_t bus){++sets;last_mapped_address=(uint32_t)bus;}
extern "C" void rdn_gart_clear_page(rdn_gart *,uint32_t){++clears;}
extern "C" int rdn_gart_flush_checked(rdn_gart *){return flush_fail?-1:0;}
int main()
{
 rdn_tiger_sleep_stage s;rdn_mem mem={0};rdn_gart gart={true};
 memset(&s,0,sizeof(s));
 assert(!rdn_tiger_sleep_stage_prepare(&s,8192) && s.prepared);
 assert(!rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart) && mem.used && sets==2 && last_mapped_address==mock_mapped_base+4096);
 assert(rdn_tiger_sleep_stage_matches(&s,&s.stage,&gart));
 gart.ready=false;assert(!rdn_tiger_sleep_stage_matches(&s,&s.stage,&gart));gart.ready=true;
 assert(rdn_tiger_sleep_stage_finish(&s) && !mock_completes);
 assert(rdn_tiger_sleep_stage_unbind_locked(&s,false) && mem.used);
 assert(!rdn_tiger_sleep_stage_unbind_locked(&s,true) && !mem.used && s.release_pending);
 assert(!rdn_tiger_sleep_stage_matches(&s,&s.stage,&gart));
 mock_complete_fail=1;assert(rdn_tiger_sleep_stage_finish(&s) && s.memory && !mock_releases);
 mock_complete_fail=0;assert(!rdn_tiger_sleep_stage_finish(&s) && !s.memory && mock_releases==1);
 memset(&s,0,sizeof(s));assert(!rdn_tiger_sleep_stage_prepare(&s,4096));flush_fail=1;
 assert(rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart) && s.stage.phase==RDN_STAGE_QUARANTINED && mem.used);
 assert(rdn_tiger_sleep_stage_finish(&s) && s.memory && mock_releases==1);
 /* Test fixture cleanup only: quarantined resources are not released in production. */
 s.memory->release();s.memory=0;mem.used=0;flush_fail=0;
 memset(&s,0,sizeof(s));mock_segment_fail=1;assert(!rdn_tiger_sleep_stage_prepare(&s,4096));
 assert(rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart) && !mem.used && s.stage.phase==RDN_STAGE_IDLE);
 assert(!rdn_tiger_sleep_stage_finish(&s));
 memset(&s,0,sizeof(s));mock_segment_fail=0;assert(!rdn_tiger_sleep_stage_prepare(&s,4096));
 assert(!rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart));
 gart.ready=false;
 assert(rdn_tiger_sleep_stage_unbind_locked(&s,true) && s.stage.phase==RDN_STAGE_QUARANTINED && mem.used && s.memory);
 assert(rdn_tiger_sleep_stage_finish(&s));
 /* Fixture cleanup only; real resources remain pinned on uncertain unbind. */
 s.memory->release();s.memory=0;mem.used=0;gart.ready=true;
 memset(&s,0,sizeof(s));mock_segment_fail=0;assert(!rdn_tiger_sleep_stage_prepare(&s,4096));
 assert(!rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart));
 rdn_quiesce q={};rdn_sleep_copy copy={};q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=7;q.internal_hold=1;
 copy.quiesce=&q;copy.generation=7;copy.stage=&s.stage;copy.transfer.phase=RDN_TRANSFER_READY;
 assert(rdn_tiger_sleep_stage_unstage_copy_locked(&s,&copy,false) && mem.used && q.internal_hold);
 assert(!rdn_tiger_sleep_stage_unstage_copy_locked(&s,&copy,true) && !mem.used && !q.internal_hold && s.release_pending);
 assert(!rdn_tiger_sleep_stage_finish(&s));
 {
  rdn_tiger_sleep_stage ib={};rdn_quiesce q2={};rdn_sleep_copy pair={};
  memset(&s,0,sizeof(s));assert(!rdn_tiger_sleep_stage_prepare(&s,4096) && !rdn_tiger_sleep_stage_prepare(&ib,4096));
  assert(!rdn_tiger_sleep_stage_bind_locked(&s,&mem,&gart) && !rdn_tiger_sleep_stage_bind_locked(&ib,&mem,&gart));
  rdn_tiger_sleep_stage_pair binding={};
  assert(!rdn_tiger_sleep_pair_init(&binding,&s,&ib));
  assert(!rdn_tiger_sleep_pair_finished(&binding,binding.data_descriptor,binding.ib_descriptor));
  q2.phase=RDN_QUIESCE_HELD_POWERED;q2.generation=8;q2.internal_hold=1;
  pair.quiesce=&q2;pair.generation=8;pair.stage=&s.stage;pair.extra_stage=&ib.stage;pair.transfer.phase=RDN_TRANSFER_READY;
  assert(rdn_tiger_sleep_stage_unstage_pair_locked(&s,&ib,&pair,false) && mem.used==2 && q2.internal_hold);
  assert(!rdn_tiger_sleep_stage_unstage_pair_locked(&s,&ib,&pair,true) && !mem.used && !q2.internal_hold);
  assert(!rdn_tiger_sleep_stage_finish(&s));
  assert(!rdn_tiger_sleep_pair_finished(&binding,binding.data_descriptor,binding.ib_descriptor));
  assert(!rdn_tiger_sleep_stage_finish(&ib));
  assert(rdn_tiger_sleep_pair_finished(&binding,binding.data_descriptor,binding.ib_descriptor));
  assert(!rdn_tiger_sleep_pair_finished(&binding,binding.ib_descriptor,binding.data_descriptor));
 }
 return 0;
}
