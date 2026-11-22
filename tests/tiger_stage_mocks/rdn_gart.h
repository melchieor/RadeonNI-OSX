#ifndef TEST_RDN_GART_H
#define TEST_RDN_GART_H
#include <stdint.h>
struct rdn_gart {bool ready;};
void rdn_gart_set_page(struct rdn_gart *,uint32_t,uint64_t);
void rdn_gart_clear_page(struct rdn_gart *,uint32_t);
int rdn_gart_flush_checked(struct rdn_gart *);
#endif
