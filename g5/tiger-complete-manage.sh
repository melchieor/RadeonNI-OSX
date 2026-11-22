#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in --verify-installed|--install|--remove) ;; *) fail 'Use --verify-installed, --install or --remove.' ;; esac
[ "$#" = 1 ] || fail 'Specify exactly one operation.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] && [ "$(uname -p)" = powerpc ] || fail 'Tiger 10.4.11 PowerPC only.'
. "$here/framebuffer-core.sh"
. "$here/graphics-core.sh"
. "$here/complete-core.sh"
rdn_complete_safe "$here/payload" || fail 'Missing or unsafe payload.'
while read expected relative; do
    [ -n "$relative" ] || fail 'Malformed payload checksum.'
    actual=$(cksum < "$here/$relative" | awk '{print $1 ":" $2}')
    [ "$actual" = "$expected" ] || fail "Payload checksum mismatch: $relative"
done <<'CHECKSUMS'
__PAYLOAD_CHECKSUMS__
CHECKSUMS
if [ "$1" = --verify-installed ]; then
    rdn_complete_verify_installed "$here/payload" /System/Library/Extensions || fail 'Installed files do not exactly match this package.'
    echo 'All six installed bundles match this package; no files changed.'
    exit 0
fi
[ "$(id -u)" = 0 ] || fail 'Run install or remove through sudo.'
loaded=$(kextstat) || fail 'Cannot inspect loaded kexts.'
if printf '%s\n' "$loaded" | grep 'org\.osxgpu\.driver\.RadeonNI' >/dev/null; then
    fail 'RadeonNI is loaded; boot with the NVIDIA card before installing or removing this package.'
fi
base='/Library/Application Support/RadeonNI'
[ -d '/Library/Application Support' ] && [ ! -L '/Library/Application Support' ] || fail 'Unexpected Application Support path.'
if [ -e "$base" ] || [ -L "$base" ]; then
    [ -d "$base" ] && [ ! -L "$base" ] || fail 'Unexpected RadeonNI support path.'
else
    [ "$1" = --install ] || fail 'No package installation state exists.'
    mkdir "$base" || fail 'Cannot create RadeonNI support directory.'
fi
state="$base/TigerComplete-__PACKAGE_ID__"
if [ "$1" = --install ]; then
    # Refuse before creating temporary copies or invalidating caches.
    for name in $rdn_complete_names; do
        [ ! -e "/System/Library/Extensions/$name" ] && [ ! -L "/System/Library/Extensions/$name" ] || fail "Existing $name: use --verify-installed or preserve it manually."
    done
    stage=$(mktemp -d /tmp/radeon-tiger-complete.XXXXXXXX) || fail 'Cannot create temporary directory.'
    trap 'rm -rf "$stage"' EXIT HUP INT TERM
    cp -R "$here/payload/RadeonNI.kext" "$stage/RadeonNI.kext"
    chown -R root:wheel "$stage/RadeonNI.kext"; chmod -R go-w "$stage/RadeonNI.kext"
    kextload -c -t -n "$stage/RadeonNI.kext" || fail 'Kext validation failed; nothing installed.'
    rdn_complete_install "$here/payload" /System/Library/Extensions "$state" root:wheel '__PACKAGE_ID__' || fail 'Install incomplete; inspect its state and files before retrying.'
else
    rdn_complete_remove "$here/payload" /System/Library/Extensions "$state" '__PACKAGE_ID__' || fail 'Removal refused; do not force it.'
fi
rm -f /System/Library/Extensions.mkext /System/Library/Extensions.kextcache || fail 'Cache invalidation failed after files changed.'
touch /System/Library/Extensions || fail 'Could not update extension timestamp after files changed.'
echo 'Restart Tiger for the change to take effect.'
