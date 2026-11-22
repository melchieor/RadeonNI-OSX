#!/bin/bash
# Compile the Leopard kernel and 2D plugin on the Intel Mac, never on the G5.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
tools=$root/third_party/leopard-toolchain/bin
sdk=$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk
out=$root/build/leopard-v7900
cc=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-gcc
cxx=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-g++
[ "$("$cc" -dumpmachine)" = powerpc-apple-darwin9 ]
mkdir -p "$out/logs"
python3 "$root/scripts/check-leopard-kext-compiler.py"
bash "$root/scripts/build-leopard-kext-arithmetic.sh"
make -B -j "${RDN_JOBS:-6}" -C "$root/kext/RadeonNI" \
    LEOPARD=1 NATIVE_KMOD_RUNTIME=1 BUILD="$out/kernel-final" \
    ARCHFLAGS=-m32 CC="$cc" CXX="$cxx" NM="$tools/nm" \
    KROOT="$sdk/System/Library/Frameworks/Kernel.framework" \
    SDKFLAGS="-isysroot $sdk -DRDN_SDK_VM_MAP_FIX=1 -DRDN_LEOPARD_FAN=1" LONG_BRANCH_FLAG=-mlongcall \
    KERNEL_CFLAGS_EXTRA='-mkernel -fno-pic -fno-PIE -fno-unwind-tables -fno-asynchronous-unwind-tables' \
    KERNEL_CXXFLAGS_EXTRA='-std=gnu++98 -fno-use-cxa-atexit -fno-threadsafe-statics' \
    KEXT_LIBS="$out/kernel-arithmetic/libkextarith.a -Wl,-new_linker"
binary=$out/kernel-final/RadeonNI.kext/Contents/MacOS/RadeonNI
RDN_OTOOL="$tools/otool" bash "$root/scripts/check-kext-relocs.sh" "$binary"
"$tools/nm" -u "$binary" > "$out/logs/kernel-final-undefined.txt"
if grep -E '^___(cxa_|dso_handle|udivdi3|ashldi3|lshrdi3|popcountsi2)|^_(rdn_|atom_)' \
    "$out/logs/kernel-final-undefined.txt"; then
    echo 'Unresolved compiler/driver symbols remain in kernel binary' >&2
    exit 1
fi
make -B -C "$root/ga" CC="$tools/powerpc-apple-darwin9-gcc" SDK="$sdk" BUILD="$out/ga-final" \
    CFLAGS="-arch ppc -Os -Wall -isysroot $sdk -I../hw -mmacosx-version-min=10.5 -nodefaultrpaths"

bash "$root/scripts/build-leopard-fan-monitor.sh"

bash "$root/scripts/build-leopard-sleep-probe.sh"
