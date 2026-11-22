#!/bin/sh
# Non-loading Tiger kext validation. No installation or GPU access.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo 'Run as root with sudo.' >&2; exit 1; }
case "$(sw_vers -productVersion)" in
10.4.11) ;;
*) echo 'This diagnostic is limited to Mac OS X 10.4.11.' >&2; exit 1 ;;
esac
[ "$(uname -p)" = powerpc ] || { echo 'This diagnostic requires PowerPC.' >&2; exit 1; }
[ -f "$here/RadeonNI.kext/Contents/MacOS/RadeonNI" ] || { echo 'Missing diagnostic kext.' >&2; exit 1; }
tmp=$(mktemp -d /tmp/radeon-tiger-probe.XXXXXXXX) || exit 1
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
cp -R "$here/RadeonNI.kext" "$tmp/RadeonNI.kext"
chown -R root:wheel "$tmp/RadeonNI.kext"
chmod -R go-w "$tmp/RadeonNI.kext"
echo 'Tiger loader probe: no driver is loaded or installed.'
echo 'The diagnostic copy is temporary and will be removed.'
sw_vers
uname -a
echo 'Already loaded relevant extensions:'
kextstat | grep -E 'RadeonNI|IOGraphicsFamily|IOPCIFamily|IONDRVSupport' || :
echo 'Beginning kextload validation and dependency checks.'
status=0
kextload -c -t -n -v 6 "$tmp/RadeonNI.kext" || status=$?
echo "kextload_exit_status=$status"
echo 'A passing result does not establish runtime or hardware safety.'
exit "$status"
