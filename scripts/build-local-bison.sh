#!/bin/bash
# Project-only parser generator for Mesa; checksum corroborated by Homebrew.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
archive=$root/third_party/bison-3.8.2.tar.xz
expected=9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ]
if [ ! -d "$root/third_party/bison-3.8.2" ]; then
    tar -xf "$archive" -C "$root/third_party"
fi
mkdir -p "$root/third_party/build-bison"
cd "$root/third_party/build-bison"
if [ ! -f Makefile ]; then
    "$root/third_party/bison-3.8.2/configure" \
        --prefix="$root/third_party/host-tools" --disable-nls --disable-dependency-tracking
fi
make -j "${RDN_JOBS:-6}"
make install
