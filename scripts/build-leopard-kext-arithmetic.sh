#!/bin/bash
# Build only the required GCC arithmetic helpers without userland unwind data.
# These are GCC Runtime Library Exception dependencies, not GPU driver sources.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
gccsrc=$root/third_party/gcc-14-darwin
gccbuild=$root/third_party/build-leopard-gcc/gcc
libgccbuild=$root/third_party/build-leopard-gcc/powerpc-apple-darwin9/libgcc
tools=$root/third_party/leopard-toolchain/bin
sdk=$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk
out=$root/build/leopard-v7900/kernel-arithmetic
mkdir -p "$out"
for routine in ashldi3 lshrdi3 popcountsi2 udivdi3; do
    "$gccbuild/xgcc" -B"$gccbuild/" -isysroot "$sdk" -m32 -Os \
        -mkernel -fno-pic -fno-PIE -fno-builtin -fno-stack-protector \
        -fno-unwind-tables -fno-asynchronous-unwind-tables \
        -DIN_GCC -DCROSS_DIRECTORY_STRUCTURE -DIN_LIBGCC2 -fbuilding-libgcc \
        -DHAVE_CC_TLS -DUSE_EMUTLS -DLIBGCC2_UNITS_PER_WORD=4 -DL_"$routine" \
        -I"$libgccbuild" -I"$gccbuild" -I"$gccsrc/libgcc" \
        -I"$gccsrc/gcc" -I"$gccsrc/include" \
        -c "$gccsrc/libgcc/libgcc2.c" -o "$out/$routine.o"
done
"$gccbuild/xgcc" -B"$gccbuild/" -m32 -mkernel -static \
    -c "$gccsrc/libgcc/config/rs6000/darwin-gpsave.S" -o "$out/gpsave.o"
"$tools/ar" rcs "$out/libkextarith.a" \
    "$out/ashldi3.o" "$out/lshrdi3.o" "$out/popcountsi2.o" "$out/udivdi3.o" "$out/gpsave.o"
"$tools/nm" -u "$out/libkextarith.a"
