#!/bin/sh
# Tiny test modules, no device personalities; kernel loading can still panic.
set -u
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
[ "$(id -u)" = 0 ] || { echo 'Run as root.' >&2; exit 1; }
cd "$(dirname "$0")" || exit 1
kextstat | grep 'org.osxgpu.driver.RadeonNI' >/dev/null || { echo 'RadeonNI is not loaded; refusing test.' >&2; exit 1; }
for name in Raw Pmap; do
 id=org.osxgpu.linkcheck.$name
 if kextstat | grep "$id" >/dev/null; then echo "Already loaded: $id; refusing test." >&2; exit 1; fi
done
tmp=$(mktemp -d /tmp/radeon-symbol-load.XXXXXXXX) || exit 1
echo "TEMPORARY_DIR=$tmp"
cp -R Raw.kext Pmap.kext "$tmp/" || exit 1
chown -R root:wheel "$tmp/Raw.kext" "$tmp/Pmap.kext" || exit 1
chmod -R go-w "$tmp/Raw.kext" "$tmp/Pmap.kext" || exit 1
keep=0
for name in Raw Pmap; do
 id=org.osxgpu.linkcheck.$name
 echo "=== $name ==="
 /sbin/kextload -c -t -n "$tmp/$name.kext" || { echo 'VALIDATION_FAILED'; exit 1; }
 /sbin/kextload -c -l -v 1 "$tmp/$name.kext"
 result=$?
 echo "LOAD_EXIT=$result"
 if kextstat | grep "$id"; then
  /sbin/kextunload -b "$id"
  unload=$?
  echo "UNLOAD_EXIT=$unload"
  if [ "$unload" != 0 ] || kextstat | grep "$id"; then keep=1; echo 'Unload uncertain; preserve temporary files and restart.'; break; fi
 fi
 echo "CASE_DONE=$name"
done
if [ "$keep" = 0 ]; then rm -rf "$tmp"; else echo "RETAINED=$tmp"; fi
kextstat | grep 'org.osxgpu.driver.RadeonNI' || { echo 'RadeonNI disappeared.' >&2; exit 1; }
[ "$keep" = 0 ] || exit 1
echo SYMBOL_LOAD_BATCH_FINISHED
