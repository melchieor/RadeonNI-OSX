#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in --install|--restore) ;; *) fail 'Use --install or --restore.' ;; esac
[ "$#" = 1 ] && [ "$(id -u)" = 0 ] || fail 'Run as root with exactly one operation.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] && [ "$(uname -p)" = powerpc ] || fail 'Tiger 10.4.11 PowerPC only.'
. "$here/framebuffer-core.sh"
. "$here/fan-core.sh"
normal="$here/normal/RadeonNI.kext"
trial="$here/trial/RadeonNI.kext"
__PAYLOAD_CHECKSUMS__
rdn_tree_safe "$normal" && rdn_tree_safe "$trial" || fail 'Payload is missing or unsafe.'
for item in normal trial; do
    eval 'expected_profile=$'"${item}_profile_cksum"
    eval 'expected_binary=$'"${item}_binary_cksum"
    actual_profile=$(cksum < "$here/$item/RadeonNI.kext/Contents/Info.plist" | awk '{print $1 ":" $2}')
    actual_binary=$(cksum < "$here/$item/RadeonNI.kext/Contents/MacOS/RadeonNI" | awk '{print $1 ":" $2}')
    [ "$actual_profile" = "$expected_profile" ] && [ "$actual_binary" = "$expected_binary" ] || fail 'Payload checksum mismatch.'
done
base='/Library/Application Support/RadeonNI'
backup="$base/TigerFanTrial-__TRIAL_ID__"
[ -d '/Library/Application Support' ] && [ ! -L '/Library/Application Support' ] || fail 'Unexpected Application Support path.'
if [ -e "$base" ] || [ -L "$base" ]; then
    [ -d "$base" ] && [ ! -L "$base" ] || fail 'Unexpected RadeonNI support path.'
else
    mkdir "$base" || fail 'Cannot create RadeonNI support directory.'
fi
if [ "$1" = --install ]; then
    # Tiger's ioreg -c includes properties and does not support -r or -l
    # combined with -c. Keep the width option separate for older versions.
    status=$(ioreg -c RadeonNI -w 0) || fail 'Cannot query framebuffer.'
    printf '%s\n' "$status" | grep '"FanControlReady" = Yes' >/dev/null || fail 'Framebuffer does not report fan control ready.'
    stage=$(mktemp -d /tmp/radeon-tiger-fancheck.XXXXXXXX) || fail 'Cannot create temporary directory.'
    trap 'rm -rf "$stage"' EXIT HUP INT TERM
    cp -R "$trial" "$stage/RadeonNI.kext"
    chown -R root:wheel "$stage/RadeonNI.kext"
    chmod -R go-w "$stage/RadeonNI.kext"
    kextload -c -t -n "$stage/RadeonNI.kext" || fail 'Kext validation failed; no installation attempted.'
    rdn_fan_install "$normal" "$trial" /System/Library/Extensions "$backup" root:wheel || fail 'Installation failed; inspect backup and installed kext before retrying.'
else
    rdn_fan_restore "$normal" "$trial" /System/Library/Extensions "$backup" root:wheel || fail 'Restore refused; do not force it. Inspect installed kext and backup.'
fi
rm -f /System/Library/Extensions.mkext /System/Library/Extensions.kextcache || fail 'Cache invalidation failed after files changed.'
touch /System/Library/Extensions || fail 'Could not update extension timestamp after files changed.'
echo 'Change is on disk; the running driver is unchanged until restart.'
