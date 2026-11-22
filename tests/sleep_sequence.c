#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_sequence.h"
static void *alloc_mem(void *p,size_t n){(void)p;return calloc(1,n);}
static void free_mem(void *p,void *v){(void)p;free(v);}
static void pattern(unsigned char *p,uint32_t word){unsigned i;for(i=0;i<4096;i++)p[i]=(unsigned char)(word>>(8*(i&3)));}
int main(void)
{
 struct rdn_os os={0};struct rdn_mem heap;struct rdn_sleep_guarded p={0};
 struct rdn_sleep_sequence s={0};struct rdn_sleep_sequence_commands cmd;uint32_t gen=0,i;
 const uint32_t patterns[]={0x13579bdfu,0x2468ace0u,0x89abcdefu};unsigned char page[4096];
 os.alloc=alloc_mem;os.free=free_mem;assert(!rdn_mem_init(&heap,&os,0x10000000,0x10000));
 assert(!rdn_sleep_guarded_acquire(&p,&heap));assert(!rdn_sleep_sequence_begin(&s));
 assert(rdn_sleep_sequence_submitted(&s,&gen));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd) && cmd.word_count==25);
 assert(rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_discard(&s));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_submitted(&s,&gen) && gen==1);
 assert(rdn_sleep_sequence_complete(&s,gen+1,1,0,0) && s.state==RDN_SEQ_WAITING);
 assert(!rdn_sleep_sequence_complete(&s,gen,1,0,0));
 for(i=0;i<3;i++) {
  assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd) && cmd.word_count==13);
  assert(!rdn_sleep_sequence_submitted(&s,&gen));pattern(page,patterns[i]);
  assert(!rdn_sleep_sequence_complete(&s,gen,1,page,4096));
 }
 assert(s.state==RDN_SEQ_CLEANUP && s.verified_mask==15);
 assert(rdn_sleep_sequence_cleanup(&s,0));assert(!rdn_sleep_sequence_cleanup(&s,1) && s.state==RDN_SEQ_PASSED);
 assert(rdn_sleep_sequence_begin(&s));
 memset(&s,0,sizeof(s));assert(!rdn_sleep_sequence_begin(&s));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_submitted(&s,&gen));assert(!rdn_sleep_sequence_complete(&s,gen,1,0,0));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_submitted(&s,&gen));pattern(page,patterns[0]);page[2]^=1;
 assert(rdn_sleep_sequence_complete(&s,gen,1,page,4096) && s.state==RDN_SEQ_CLEANUP && s.mismatches[0]==1);
 assert(!rdn_sleep_sequence_cleanup(&s,1) && s.state==RDN_SEQ_FAILED);
 memset(&s,0,sizeof(s));assert(!rdn_sleep_sequence_begin(&s));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_submitted(&s,&gen));assert(!rdn_sleep_sequence_uncertain(&s,gen));
 assert(s.state==RDN_SEQ_QUARANTINED && rdn_sleep_sequence_cleanup(&s,1));
 memset(&s,0,sizeof(s));assert(!rdn_sleep_sequence_begin(&s));
 assert(!rdn_sleep_sequence_build(&s,&p,0,0x80000000,0x10000000,0x80001000,0x80002000,&cmd));
 assert(!rdn_sleep_sequence_submitted(&s,&gen));assert(rdn_sleep_sequence_complete(&s,gen,0,0,0));
 assert(s.state==RDN_SEQ_QUARANTINED && rdn_sleep_sequence_cleanup(&s,1));
 assert(!rdn_sleep_guarded_release(&p,1));rdn_mem_fini(&heap);return 0;
}
