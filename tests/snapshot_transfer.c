#include <assert.h>
#include "rdn_snapshot_transfer.h"
int main(void)
{
 struct rdn_snapshot_transfer t={0,0};
 assert(rdn_transfer_prepare(&t,0,1));assert(rdn_transfer_prepare(&t,1,0));
 assert(!rdn_transfer_prepare(&t,1,1));assert(!rdn_transfer_submitted(&t,0));
 assert(!rdn_transfer_complete(&t,0,1));assert(!rdn_transfer_release(&t));
 assert(!rdn_transfer_prepare(&t,1,1));
 assert(!rdn_transfer_abort_before_submit(&t));assert(!rdn_transfer_prepare(&t,1,1));
 assert(!rdn_transfer_submitted(&t,7));assert(rdn_transfer_release(&t));
 assert(rdn_transfer_abort_before_submit(&t));assert(rdn_transfer_complete(&t,8,1));
 assert(rdn_transfer_complete(&t,7,0));assert(!rdn_transfer_complete(&t,7,1));
 assert(!rdn_transfer_release(&t));assert(!rdn_transfer_prepare(&t,1,1));
 assert(!rdn_transfer_submitted(&t,9));assert(!rdn_transfer_uncertain(&t));
 assert(rdn_transfer_complete(&t,9,1));assert(rdn_transfer_release(&t));
 assert(rdn_transfer_prepare(&t,1,1));assert(t.phase==RDN_TRANSFER_QUARANTINED);
 t.phase=RDN_TRANSFER_IDLE;t.fence=0; /* Fresh fixture, not a recovery operation. */
 assert(!rdn_transfer_prepare(&t,1,1));assert(!rdn_transfer_uncertain(&t));
 assert(rdn_transfer_abort_before_submit(&t));assert(rdn_transfer_release(&t));
 return 0;
}
