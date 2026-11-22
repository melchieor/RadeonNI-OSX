#!/bin/bash
# Build diagnostic tools on the Intel Mac, not on the Power Mac.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cc=$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc
sdk=$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk
out=$root/build/leopard-v7900
mkdir -p "$out/qe-probes"
common=(-arch ppc -Os -Wall -std=gnu99 -isysroot "$sdk" -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error -I"$root/hw" -I"$root/tools/guest")
"$cc" "${common[@]}" "$root/tools/guest/leopard-qe-status.c" \
 -framework ApplicationServices -framework OpenGL -o "$out/qe-probes/qe-status"
"$cc" "${common[@]}" "$root/tools/guest/wsfilter.c" \
 -framework Carbon -framework ApplicationServices -o "$out/qe-probes/ci-filter-test"
"$cc" "${common[@]}" "$root/tools/guest/backingsurfacetest.c" \
 -framework OpenGL -framework IOKit -framework ApplicationServices -o "$out/qe-probes/backing-test"
