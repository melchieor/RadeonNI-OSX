#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in --install|--restore) ;; *) fail 'Use --install or --restore.' ;; esac
[ "$#" = 1 ] && [ "$(id -u)" = 0 ] || fail 'Run through sudo with one operation.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] && [ "$(uname -p)" = powerpc ] || fail 'Tiger 10.4.11 PowerPC only.'
. "$here/framebuffer-core.sh"
. "$here/graphics-core.sh"
rdn_graphics_verify_payload "$here" || fail 'Payload missing or unsafe.'
while read expected relative; do
    [ -n "$relative" ] || fail 'Malformed checksum entry.'
    actual=$(cksum < "$here/$relative" | awk '{print $1 ":" $2}')
    [ "$actual" = "$expected" ] || fail "Checksum mismatch: $relative"
done <<'CHECKSUMS'
__PAYLOAD_CHECKSUMS__
CHECKSUMS
base='/Library/Application Support/RadeonNI'
backup="$base/TigerGraphicsTrial-__TRIAL_ID__"
[ -d "$base" ] && [ ! -L "$base" ] || fail 'RadeonNI support directory missing or unsafe.'
if [ "$1" = --install ]; then
    status=$(ioreg -c RadeonNIAccel -w 0) || fail 'Cannot query accelerator.'
    printf '%s\n' "$status" | grep '"RadeonNIEngine" = Yes' >/dev/null || fail 'Running engine is not ready.'
    stage=$(mktemp -d /tmp/radeon-tiger-graphics.XXXXXXXX) || fail 'Cannot create temporary directory.'
    trap 'rm -rf "$stage"' EXIT HUP INT TERM
    cp -R "$here/trial/RadeonNI.kext" "$stage/RadeonNI.kext"
    chown -R root:wheel "$stage/RadeonNI.kext"
    chmod -R go-w "$stage/RadeonNI.kext"
    kextload -c -t -n "$stage/RadeonNI.kext" || fail 'Kext validation failed; no installation attempted.'
    rdn_graphics_install "$here" /System/Library/Extensions "$backup" root:wheel || fail 'Installation failed; inspect backup and installed files before retrying.'
else
    rdn_graphics_restore "$here" /System/Library/Extensions "$backup" root:wheel || fail 'Restore refused; do not force it. Inspect backup and installed files.'
fi
rm -f /System/Library/Extensions.mkext /System/Library/Extensions.kextcache || fail 'Cache invalidation failed after files changed.'
touch /System/Library/Extensions || fail 'Could not update extension timestamp after files changed.'
echo 'Change is on disk; running graphics components remain unchanged until restart.'
