#!/bin/bash
# Build an uninstalled indexed-VRAM diagnostic kext on the Intel Mac.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
sdk=$root/build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk
tag=${RDN_SLEEP_LINK_TAG:-indexed-vram}
case "$tag" in *[!a-zA-Z0-9-]*) echo 'Invalid probe tag.' >&2; exit 1;; esac
out=$root/build/tiger-v7900/sleep-index-probe${tag:+-$tag}
tools=$root/third_party/leopard-toolchain/bin
cc=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-gcc
cxx=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-g++
arith=$root/build/tiger-v7900/kernel-arithmetic/libkextarith.a
[ -r "$arith" ] && [ -d "$sdk/System/Library/Frameworks/Kernel.framework" ]
mkdir "$out" || { echo 'Output exists; refusing to overwrite it.' >&2; exit 1; }
echo 'EXPERIMENTAL diagnostic kext; do not use without profile, validation and recovery.'
if [ "${RDN_PHYSICAL_ADDRESS_VERIFIED:-0}" != 0 ]; then
 echo 'Physical mapping probe is quarantined after a G5 panic; refusing to build.' >&2
 exit 1
fi
make -B -j "${RDN_JOBS:-6}" -C "$root/kext/RadeonNI" LEOPARD=0 TIGER_COMPAT=1 \
 SLEEP_INDEX_PROBE=1 NATIVE_KMOD_RUNTIME=1 BUILD="$out/kernel" ARCHFLAGS=-m32 \
 CC="$cc" CXX="$cxx" NM="$tools/nm" KROOT="$sdk/System/Library/Frameworks/Kernel.framework" \
 SDKFLAGS="-isysroot $sdk -mmacosx-version-min=10.4 -DRDN_SDK_VM_MAP_FIX=1 -DRDN_TIGER_FAN=1" \
 LONG_BRANCH_FLAG=-mlongcall \
 KERNEL_CFLAGS_EXTRA='-mkernel -fno-pic -fno-PIE -fno-unwind-tables -fno-asynchronous-unwind-tables' \
 KERNEL_CXXFLAGS_EXTRA='-std=gnu++98 -fpermissive -fno-use-cxa-atexit -fno-threadsafe-statics' \
 KEXT_LIBS="$arith -Wl,-new_linker"
file "$out/kernel/RadeonNI.kext/Contents/MacOS/RadeonNI"
