#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
case "${1:-}" in
    --check|--check-before-swap|--install|--prepare-swap) ;;
    *) echo 'usage: sudo sh install.sh --check|--check-before-swap|--install|--prepare-swap' >&2; exit 1 ;;
esac
[ "$#" = 1 ] || { echo 'Specify exactly one operation' >&2; exit 1; }
[ "$(uname -p)" = powerpc ] || { echo 'PowerPC only' >&2; exit 1; }
case "$(sw_vers -productVersion)" in 10.5.8|10.5.9) ;; *) echo 'Leopard 10.5.8 / Sorbet 10.5.9 only' >&2; exit 1 ;; esac
[ "$(id -u)" = 0 ] || { echo 'Run through sudo' >&2; exit 1; }
/usr/bin/python -E -S "$here/manage.py" verify
if [ "$1" = --prepare-swap ] || [ "$1" = --check-before-swap ]; then
    echo 'Preparing for a card swap: V7900 presence is not required.'
    echo 'This checks kernel loadability only; AMD display operation remains untested.'
else
ioreg -p IODeviceTree -l -w0 | grep -Ei '(pci|pciex)1002,6704' >/dev/null || {
    echo 'No V7900 (1002:6704) found in the device tree. Use --prepare-swap only to install before swapping cards.' >&2; exit 1;
}
fi
stage=$(mktemp -d /tmp/RadeonNI-V7900.XXXXXX)
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM
cp -R "$here/payload/RadeonNI.kext" "$stage/"
chown -R root:wheel "$stage/RadeonNI.kext"
chmod -R go-w "$stage/RadeonNI.kext"
# -t -n alone validates metadata but skips the executable linker. Request
# symbols at synthetic addresses to exercise Leopard's C++ patcher/linker
# without loading the extension or publishing its personalities.
mkdir "$stage/symbols"
if kextload -t -n -v 6 -s "$stage/symbols" \
    -a com.apple.iokit.IOPCIFamily@0x10000000 \
    -a com.apple.iokit.IOGraphicsFamily@0x10200000 \
    -a org.osxgpu.driver.RadeonNI@0x10400000 \
    "$stage/RadeonNI.kext" > "$stage/link.log" 2>&1; then
    cat "$stage/link.log"
else
    cat "$stage/link.log" >&2
    echo 'Native linker check failed. No driver files installed.' >&2
    exit 1
fi
if grep -Ei 'not compatible with its superclass|link/load error|undefined symbols|unresolved symbols|failed to link' "$stage/link.log" >/dev/null; then
    echo 'Native linker reported an error. No driver files installed.' >&2
    exit 1
fi
[ -s "$stage/symbols/org.osxgpu.driver.RadeonNI.sym" ] || {
    echo 'Native linker produced no RadeonNI symbols; refusing installation.' >&2
    exit 1
}
if [ "$1" = --check ] || [ "$1" = --check-before-swap ]; then
    echo 'Native kernel link check passed (synthetic addresses, no execution). No installed driver files were changed.'
    exit 0
fi
/usr/bin/python -E -S "$here/manage.py" install
if [ "$1" = --prepare-swap ]; then
    echo 'Prepared for card swap. Save the backup path printed above.'
    echo 'Shut down and unplug the G5 before replacing the NVIDIA card and transferring its power lead.'
    echo 'Keep the NVIDIA card available for recovery. No reboot or driver loading was performed.'
fi
