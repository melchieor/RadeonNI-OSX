#!/bin/bash
# Precompile offscreen diagnostics on Intel Mac; no target installation.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/build/leopard-v7900/pixel-probe"
mkdir -p "$out"
for shape in small odd large atlas; do
 case "$shape" in
 small) width=64; height=32; suffix= ;;
 odd) width=257; height=129; suffix=-odd ;;
 large) width=1024; height=256; suffix=-large ;;
 atlas) width=320; height=320; suffix=-atlas ;;
 esac
"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" \
 -arch ppc -Os -Wall -Wextra -std=gnu99 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" \
 -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error \
 -DTW="$width" -DTH="$height" -I"$root/tools/guest" "$root/tools/guest/pixel-render-probe.c" \
 -framework OpenGL -o "$out/pixel-render-probe$suffix"
done

# Additional bounded rendering checks; no installed files are changed.
common=(-arch ppc -Os -Wall -std=gnu99 -isysroot "$root/third_party/sdk-audit/extracted/MacOSX10.5.sdk" -mmacosx-version-min=10.5 -nodefaultrpaths -static-libgcc -Wl,-undefined,error -I"$root/hw" -I"$root/tools/guest")
for name in sharetest contexthandofftest pbufferlifetest pbufferpublishtest pbufferthreadtest; do
 "$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" "${common[@]}" "$root/tools/guest/$name.c" -framework OpenGL -o "$out/$name"
done
"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" "${common[@]}" "$root/tools/guest/backingsurfacetest.c" -framework OpenGL -framework IOKit -framework ApplicationServices -o "$out/backingsurfacetest"
"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" "${common[@]}" "$root/tools/guest/rendering-suite-visual.m" -framework Cocoa -framework OpenGL -o "$out/rendering-suite-visual"

"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" "${common[@]}" -dynamiclib "$root/tools/guest/preferences-capture.c" -framework CoreFoundation -Wl,-install_name,@loader_path/preferences-capture.dylib -o "$out/preferences-capture.dylib"

"$root/third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc" "${common[@]}" "$root/tools/guest/capture-preflight.c" -framework CoreFoundation -framework OpenGL -o "$out/capture-preflight"
