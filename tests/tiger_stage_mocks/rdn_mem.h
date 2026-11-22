#ifndef TEST_RDN_MEM_H
#define TEST_RDN_MEM_H
#include <stdint.h>
struct rdn_mem {int used;};
int rdn_mem_alloc(struct rdn_mem *,uint64_t,uint64_t,uint64_t *);
void rdn_mem_free(struct rdn_mem *,uint64_t);
#endif
