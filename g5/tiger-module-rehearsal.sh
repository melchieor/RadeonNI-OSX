#!/bin/sh
# Experimental module registration only. It can panic the computer.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
[ "${1:-}" = '--i-understand-runtime-risk' ] && [ "$#" = 1 ] || fail 'Read README.txt, then supply --i-understand-runtime-risk.'
[ "$(id -u)" = 0 ] || fail 'Run with sudo.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] || fail 'Mac OS X 10.4.11 is required.'
[ "$(uname -p)" = powerpc ] || fail 'PowerPC is required.'
[ ! -e /System/Library/Extensions/RadeonNI.kext ] || fail 'A RadeonNI.kext already exists in /System/Library/Extensions.'
if kextstat | grep -q 'org\.osxgpu\.driver\.RadeonNI'; then
    fail 'RadeonNI is already loaded; reboot before this experiment.'
fi
[ -f "$here/RadeonNI.kext/Contents/MacOS/RadeonNI" ] || fail 'Diagnostic module is missing.'
tmp=$(mktemp -d /tmp/radeon-tiger-module.XXXXXXXX) || fail 'Cannot create temporary directory.'
echo "Temporary module directory: $tmp"
cp -R "$here/RadeonNI.kext" "$tmp/RadeonNI.kext"
chown -R root:wheel "$tmp/RadeonNI.kext"
chmod -R go-w "$tmp/RadeonNI.kext"
echo 'Validating module before load:'
kextload -c -t -n "$tmp/RadeonNI.kext" || fail 'Pre-load validation failed; no load attempted.'
echo 'Loading module without a device-matching profile; a kernel panic remains possible.'
status=0
kextload -c -l -v 1 "$tmp/RadeonNI.kext" || status=$?
echo "kextload_exit_status=$status"
echo 'Loaded matching extensions:'
kextstat | grep 'org\.osxgpu\.driver\.RadeonNI' || :
echo 'The module is not installed. Do not remove the temporary directory while it may be loaded.'
echo 'After recording the result, restart Tiger to clear any loaded test module.'
exit "$status"
