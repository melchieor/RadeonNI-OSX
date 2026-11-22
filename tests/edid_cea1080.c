/* CEA VIC 16 and DMT 1920x1080 use different sync polarities. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "rdn_mode.h"

int main(void)
{
    unsigned i;
    int n, pref = 0, found = 0;
    uint8_t edid[256];
    struct rdn_mode modes[32];
    memset(edid, 0, sizeof(edid));
    edid[18] = 1; edid[19] = 3;
    for (i = 38; i < 54; ++i) edid[i] = 1;
    edid[126] = 1;
    edid[128] = 2;  /* CEA extension */
    edid[130] = 6;  /* detailed timing area begins after video block */
    edid[132] = 0x41; edid[133] = 16; /* video data block, VIC 16 */
    n = rdn_edid_modes(edid, sizeof(edid), modes, 32, &pref);
    for (i = 0; i < (unsigned)n; ++i) {
        if (modes[i].hdisplay == 1920 && modes[i].vdisplay == 1080) {
            assert(modes[i].clock == 148500);
            assert(modes[i].flags == 0); /* +HSync +VSync */
            ++found;
        }
    }
    assert(found == 1);
    puts("PASS: CEA VIC 16 publishes one 1080p60 mode with positive syncs");
    return 0;
}
