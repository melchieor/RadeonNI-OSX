/* Transfer lifetime model: no hardware access or implicit quarantine clearing. */
#include "rdn_snapshot_transfer.h"
int rdn_transfer_prepare(struct rdn_snapshot_transfer *t,int pinned,int gated)
{
 if(!t || t->phase!=RDN_TRANSFER_IDLE || !pinned || !gated)return -1;
 t->fence=0;t->phase=RDN_TRANSFER_PREPARED;return 0;
}
int rdn_transfer_submitted(struct rdn_snapshot_transfer *t,uint32_t fence)
{
 if(!t || t->phase!=RDN_TRANSFER_PREPARED)return -1;
 t->fence=fence;t->phase=RDN_TRANSFER_INFLIGHT;return 0;
}
int rdn_transfer_complete(struct rdn_snapshot_transfer *t,uint32_t fence,int synced)
{
 if(!t || t->phase!=RDN_TRANSFER_INFLIGHT || fence!=t->fence || !synced)return -1;
 t->phase=RDN_TRANSFER_READY;return 0;
}
int rdn_transfer_abort_before_submit(struct rdn_snapshot_transfer *t)
{
 if(!t || t->phase!=RDN_TRANSFER_PREPARED)return -1;
 t->phase=RDN_TRANSFER_IDLE;t->fence=0;return 0;
}
int rdn_transfer_uncertain(struct rdn_snapshot_transfer *t)
{
 if(!t || (t->phase!=RDN_TRANSFER_PREPARED && t->phase!=RDN_TRANSFER_INFLIGHT && t->phase!=RDN_TRANSFER_READY))return -1;
 t->phase=RDN_TRANSFER_QUARANTINED;return 0;
}
int rdn_transfer_release(struct rdn_snapshot_transfer *t)
{
 if(!t || t->phase!=RDN_TRANSFER_READY)return -1;
 t->phase=RDN_TRANSFER_IDLE;t->fence=0;return 0;
}
