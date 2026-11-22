#!/bin/bash
# EXPERIMENT ONLY: Tiger SDK compilation on the build Mac; not installable.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
sdk=$root/build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk
out=$root/build/tiger-v7900
fanflag=
kernel_build="$out/kernel-experiment"
case "${RDN_TIGER_FAN_TEST:-0}" in
 0) ;;
 1) fanflag=-DRDN_TIGER_FAN=1; kernel_build="$out/kernel-fan-experiment" ;;
 *) echo 'RDN_TIGER_FAN_TEST must be 0 or 1' >&2; exit 1 ;;
esac
ga_build="$out/ga-experiment"
case "${RDN_TIGER_CINEMA_TEST:-0}" in
 0) ;;
 1) [ "${RDN_TIGER_FAN_TEST:-0}" = 1 ] || { echo 'Cinema trial requires the fan test build' >&2; exit 1; }
    kernel_build="$out/kernel-cinema-experiment"; ga_build="$out/ga-cinema-experiment" ;;
 *) echo 'RDN_TIGER_CINEMA_TEST must be 0 or 1' >&2; exit 1 ;;
esac
gccsrc=$root/third_party/gcc-14-darwin
gccbuild=$root/third_party/build-leopard-gcc/gcc
libgccbuild=$root/third_party/build-leopard-gcc/powerpc-apple-darwin9/libgcc
tools=$root/third_party/leopard-toolchain/bin
cc=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-gcc
cxx=$root/third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-g++
[ -d "$sdk/System/Library/Frameworks/Kernel.framework" ]
mkdir -p "$out/kernel-arithmetic" "$out/logs"
for routine in ashldi3 lshrdi3 popcountsi2 udivdi3; do
 "$gccbuild/xgcc" -B"$gccbuild/" -isysroot "$sdk" -mmacosx-version-min=10.4 -m32 -Os \
  -mkernel -fno-pic -fno-PIE -fno-builtin -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables \
  -DIN_GCC -DCROSS_DIRECTORY_STRUCTURE -DIN_LIBGCC2 -fbuilding-libgcc -DHAVE_CC_TLS -DUSE_EMUTLS \
  -DLIBGCC2_UNITS_PER_WORD=4 -DL_"$routine" -I"$libgccbuild" -I"$gccbuild" -I"$gccsrc/libgcc" \
  -I"$gccsrc/gcc" -I"$gccsrc/include" -c "$gccsrc/libgcc/libgcc2.c" -o "$out/kernel-arithmetic/$routine.o"
done
"$gccbuild/xgcc" -B"$gccbuild/" -m32 -mkernel -static -c "$gccsrc/libgcc/config/rs6000/darwin-gpsave.S" -o "$out/kernel-arithmetic/gpsave.o"
"$tools/ar" rcs "$out/kernel-arithmetic/libkextarith.a" "$out/kernel-arithmetic/ashldi3.o" "$out/kernel-arithmetic/lshrdi3.o" "$out/kernel-arithmetic/popcountsi2.o" "$out/kernel-arithmetic/udivdi3.o" "$out/kernel-arithmetic/gpsave.o"
make -B -j "${RDN_JOBS:-6}" -C "$root/kext/RadeonNI" LEOPARD=0 TIGER_COMPAT=1 NATIVE_KMOD_RUNTIME=1 \
 BUILD="$kernel_build" ARCHFLAGS=-m32 CC="$cc" CXX="$cxx" NM="$tools/nm" \
 KROOT="$sdk/System/Library/Frameworks/Kernel.framework" \
 SDKFLAGS="-isysroot $sdk -mmacosx-version-min=10.4 -DRDN_SDK_VM_MAP_FIX=1 $fanflag" LONG_BRANCH_FLAG=-mlongcall \
 KERNEL_CFLAGS_EXTRA='-mkernel -fno-pic -fno-PIE -fno-unwind-tables -fno-asynchronous-unwind-tables' \
 KERNEL_CXXFLAGS_EXTRA='-std=gnu++98 -fpermissive -fno-use-cxa-atexit -fno-threadsafe-statics' \
 KEXT_LIBS="$out/kernel-arithmetic/libkextarith.a -Wl,-new_linker"
make -B -C "$root/ga" CC="$tools/powerpc-apple-darwin9-gcc" SDK="$sdk" BUILD="$ga_build" \
 CFLAGS="-m32 -Os -Wall -isysroot $sdk -I../hw -mmacosx-version-min=10.4 -nodefaultrpaths"
echo 'EXPERIMENTAL: fan build flag='"${RDN_TIGER_FAN_TEST:-0}"
echo 'EXPERIMENTAL: ABI, kernel import closure and runtime behavior are not qualified. Do not install.'
