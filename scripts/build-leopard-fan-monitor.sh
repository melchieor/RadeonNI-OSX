#!/bin/bash
# Read-only telemetry utility, compiled on the Intel Mac only.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" \
 -arch ppc -Os -Wall -std=gnu99 -mmacosx-version-min=10.5 -nodefaultrpaths \
 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" -I"$root/hw" \
 "$root/tools/guest/fanmonitor.c" -framework IOKit -framework CoreFoundation \
 -static-libgcc -Wl,-undefined,error -o "$root/build/leopard-v7900/fan-monitor"
