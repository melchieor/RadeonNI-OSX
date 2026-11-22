#!/bin/bash
# Build on Intel macOS only. This program never requests system sleep.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" \
 -arch ppc -Os -Wall -std=gnu99 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" \
 -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error \
 -I"$root/hw" -I"$root/tools/guest" "$root/tools/guest/sleep-rehearsal.c" \
 -framework IOKit -framework CoreFoundation -o "$root/build/leopard-v7900/sleep-rehearsal"

"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" \
 -arch ppc -Os -Wall -std=gnu99 -DRDN_MAINTENANCE_PROBE=1 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" \
 -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error \
 -I"$root/hw" -I"$root/tools/guest" "$root/tools/guest/sleep-rehearsal.c" \
 -framework IOKit -framework CoreFoundation -o "$root/build/leopard-v7900/maintenance-rehearsal"

"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" \
 -arch ppc -Os -Wall -std=gnu99 -DRDN_MAINTENANCE_PROBE=1 -DRDN_RESOURCE_PROBE=1 \
 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" \
 -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error \
 -I"$root/hw" -I"$root/tools/guest" "$root/tools/guest/sleep-rehearsal.c" \
 -framework IOKit -framework CoreFoundation -o "$root/build/leopard-v7900/resource-rehearsal"
