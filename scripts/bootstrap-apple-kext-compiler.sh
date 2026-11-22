#!/bin/bash
# Build Apple's PPC kernel C++ ABI1 compiler on the Intel Mac, locally only.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
tp=$root/third_party
source=$tp/apple-gcc-abi-reference
archive=$tp/apple-gcc-24a5ff4.tar.gz
pin=24a5ff4087d09b1170bc4653c85bf2d8361b2320
expected=9543e0f5a2ac116ee7f4b9e347bb25ad7339f99c5e91aa2cd2f02575cd37dd4e
prefix=$tp/apple-kext-toolchain
sdk=$tp/sdk-audit/extracted/MacOSX10.5.sdk
build=$tp/build-apple-gcc-abi
logs=$root/build/leopard-v7900/logs
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ]
mkdir -p "$tp" "$logs" "$build"
if [ ! -f "$archive" ]; then
    curl --fail --location --retry 2 "https://codeload.github.com/apple-oss-distributions/gcc/tar.gz/$pin" -o "$archive.partial"
    mv "$archive.partial" "$archive"
fi
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ]
if [ ! -d "$source" ]; then
    mkdir "$source"
    tar -xzf "$archive" -C "$source" --strip-components=1
fi
change=$root/scripts/toolchain-patches/apple-gcc42-kernel-longcall-islands.patch
if ! patch -d "$source" -p1 -R --dry-run -s -f < "$change" >/dev/null 2>&1; then
    patch -d "$source" -p1 -F 0 --batch --forward < "$change"
fi
export PATH="$tp/leopard-toolchain/target-tools:$PATH"
cd "$build"
if [ ! -f Makefile ]; then
    # Host warning switches belong to CC, not CFLAGS: old GCC also uses
    # CFLAGS for target startup files, where modern Clang switches are invalid.
    CC='clang -Wno-error=implicit-function-declaration -Wno-error=int-conversion' \
    CXX=clang++ CFLAGS='-O2 -std=gnu89' \
    "$source/configure" --build=x86_64-apple-darwin25 --host=x86_64-apple-darwin25 \
        --target=powerpc-apple-darwin9 --prefix="$prefix" \
        --enable-languages=c,c++ --disable-bootstrap --disable-multilib \
        --disable-nls --disable-werror --with-sysroot="$sdk" \
        --with-as="$tp/leopard-toolchain/target-tools/powerpc-apple-darwin9-as" \
        --with-ld="$tp/leopard-toolchain/bin/ld" 2>&1 | tee "$logs/apple-gcc-configure.log"
fi
make -j "${RDN_JOBS:-6}" all-gcc CFLAGS='-O2 -std=gnu89' 2>&1 | tee "$logs/apple-gcc-build-final.log"
make install-gcc CFLAGS='-O2 -std=gnu89' 2>&1 | tee "$logs/apple-gcc-install.log"
"$prefix/bin/powerpc-apple-darwin9-g++" --version
