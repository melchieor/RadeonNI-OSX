/* Model-specific, opt-in 1080p timing must not affect other monitors. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "rdn_mode.h"

static void fix_checksum(unsigned char *e)
{
    unsigned i, sum=0;
    e[127]=0;
    for(i=0;i<127;++i) sum+=e[i];
    e[127]=(unsigned char)(0-sum);
}

int main(void)
{
    static const unsigned char header[8]={0,255,255,255,255,255,255,0};
    static const unsigned char native[18]={0x56,0x5e,0x00,0xa0,0xa0,0xa0,0x29,0x50,0x30,0x20,0x35,0x00,0x55,0x50,0x21,0x00,0x00,0x1a};
    unsigned char e[128]={0};
    struct rdn_mode modes[32], saved[32];
    int n, pref=0, old;
    memcpy(e,header,sizeof(header));e[8]=0x06;e[9]=0x10;e[10]=0x26;e[11]=0x92;
    e[18]=1;e[19]=4;memset(e+38,1,16);memcpy(e+54,native,sizeof(native));fix_checksum(e);
    n=rdn_edid_modes(e,sizeof(e),modes,32,&pref);old=n;memcpy(saved,modes,sizeof(modes));
    n=rdn_edid_add_apple_cinema_1080p(e,sizeof(e),modes,n,32);
    assert(n==old+1 && modes[n-1].hdisplay==1920 && modes[n-1].vdisplay==1080);
    assert(modes[n-1].clock==148500 && modes[n-1].flags==0 && pref==0);
    assert(rdn_edid_add_apple_cinema_1080p(e,sizeof(e),modes,n,32)==n);
    assert(rdn_edid_add_apple_cinema_1080p(e,sizeof(e),saved,old,old)==old);
    e[10]^=1;fix_checksum(e);
    assert(rdn_edid_add_apple_cinema_1080p(e,sizeof(e),saved,old,32)==old);
    e[10]^=1;fix_checksum(e);e[20]^=1; /* invalid checksum */
    assert(rdn_edid_add_apple_cinema_1080p(e,sizeof(e),saved,old,32)==old);
    e[20]^=1; /* add contradictory display range descriptor */
    e[72]=0;e[73]=0;e[75]=0xfd;e[77]=40;e[78]=50;e[79]=1;e[80]=255;e[81]=0xff;fix_checksum(e);
    assert(rdn_edid_add_apple_cinema_1080p(e,sizeof(e),saved,old,32)==old);
    puts("PASS: opt-in Cinema 1080p scope, checksum, range and duplicate guards");
    return 0;
}
