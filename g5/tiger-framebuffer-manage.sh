#!/bin/sh
# First framebuffer-only experiment for Tiger. Requires the NVIDIA fallback.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in --install|--remove) ;; *) fail 'Use --install or --remove.' ;; esac
[ "$#" = 1 ] || fail 'Supply one operation.'
[ "$(id -u)" = 0 ] || fail 'Run with sudo.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] || fail 'Tiger 10.4.11 only.'
[ "$(uname -p)" = powerpc ] || fail 'PowerPC only.'
bundle="$here/payload/RadeonNI.kext"
. "$here/core.sh"
rdn_tree_safe "$bundle" || fail 'Package payload is missing or unsafe.'
plist_cksum=$(cksum < "$bundle/Contents/Info.plist" | awk '{print $1 ":" $2}')
binary_cksum=$(cksum < "$bundle/Contents/MacOS/RadeonNI" | awk '{print $1 ":" $2}')
[ "$plist_cksum" = '__EXPECTED_PLIST_CKSUM__' ] || fail 'Payload profile checksum mismatch.'
[ "$binary_cksum" = '__EXPECTED_BINARY_CKSUM__' ] || fail 'Payload binary checksum mismatch.'
loaded=$(kextstat) || fail 'Could not inspect loaded extensions.'
if printf '%s\n' "$loaded" | grep -q 'org\.osxgpu\.driver\.RadeonNI'; then
    fail 'RadeonNI is loaded. Boot with the NVIDIA card and restart before changing it.'
fi
if [ "$1" = --install ]; then
    [ ! -e /System/Library/Extensions/RadeonNI.kext ] && [ ! -L /System/Library/Extensions/RadeonNI.kext ] || fail 'An existing RadeonNI.kext must be preserved; installation refused.'
    stage=$(mktemp -d /tmp/radeon-tiger-check.XXXXXXXX) || fail 'Could not create temporary directory.'
    trap 'rm -rf "$stage"' EXIT HUP INT TERM
    cp -R "$bundle" "$stage/RadeonNI.kext"
    chown -R root:wheel "$stage/RadeonNI.kext"
    chmod -R go-w "$stage/RadeonNI.kext"
    kextload -c -t -n "$stage/RadeonNI.kext" || fail 'Kext validation failed; nothing installed.'
    rdn_install "$bundle" /System/Library/Extensions root:wheel || fail 'Installation failed; inspect /System/Library/Extensions/RadeonNI.kext before retrying.'
    echo 'Framebuffer kext installed; it will not be loaded by this script.'
else
    rdn_remove "$bundle" /System/Library/Extensions || fail 'Removal refused; installed files must match this package.'
    echo 'Matching framebuffer kext removed.'
fi
# Tiger can regenerate these system extension caches after their invalidation.
rm -f /System/Library/Extensions.mkext /System/Library/Extensions.kextcache || fail 'Could not invalidate caches; driver file changes may already have occurred.'
touch /System/Library/Extensions || fail 'Could not update extension timestamp; driver file changes may already have occurred.'
echo 'Extension caches invalidated. Restart Tiger for the change to take effect.'
