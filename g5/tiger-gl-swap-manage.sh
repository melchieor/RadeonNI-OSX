#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in --install|--restore) ;; *) fail 'Use --install or --restore.' ;; esac
[ "$#" = 1 ] && [ "$(id -u)" = 0 ] || fail 'Run through sudo with one operation.'
[ "$(sw_vers -productVersion)" = 10.4.11 ] && [ "$(uname -p)" = powerpc ] || fail 'Tiger 10.4.11 PowerPC only.'
. "$here/swap-core.sh"
while read expected relative; do
    [ -n "$relative" ] || fail 'Malformed checksum entry.'
    actual=$(cksum < "$here/$relative" | awk '{print $1 ":" $2}')
    [ "$actual" = "$expected" ] || fail "Checksum mismatch: $relative"
done <<'CHECKSUMS'
__PAYLOAD_CHECKSUMS__
CHECKSUMS
base='/Library/Application Support/RadeonNI'
[ -d "$base" ] && [ ! -L "$base" ] || fail 'RadeonNI support directory missing or unsafe.'
backup="$base/TigerCFMGLTrial-__TRIAL_ID__"
if [ "$1" = --install ]; then
    status=$(ioreg -c RadeonNIAccel -w 0) || fail 'Cannot query accelerator.'
    printf '%s\n' "$status" | grep '"RadeonNIEngine" = Yes' >/dev/null || fail 'Running engine is not ready.'
    rdn_gl_install "$here" /System/Library/Extensions "$backup" root:wheel || fail 'Installation failed; inspect the backup and installed files before retrying.'
else
    rdn_gl_restore "$here" /System/Library/Extensions "$backup" root:wheel || fail 'Restore refused; inspect the backup and installed files.'
fi
echo 'Only GL bundle executables changed. Quit and relaunch test applications.'
echo 'Processes already using the old executables may retain them until they exit.'
