#!/bin/bash
# Native Intel macOS -> PowerPC Darwin 9 bootstrap. Installs only in third_party.
# Requires the separately approved Homebrew CMake, Ninja, GMP, MPFR and MPC.
set -euo pipefail
export LC_ALL=C
# Older libtool queries sysctl, which may be denied in a build sandbox.
# Use the POSIX query and retain its own fourfold safety margin instead.
export lt_cv_sys_max_cmd_len=$(( $(getconf ARG_MAX) / 4 ))
root=$(cd "$(dirname "$0")/.." && pwd)
tp=$root/third_party
prefix=$tp/leopard-toolchain
sdk=$tp/sdk-audit/extracted/MacOSX10.5.sdk
xtools=$tp/darwin-xtools
gcc=$tp/gcc-14-darwin
logs=$root/build/leopard-v7900/logs
jobs=${RDN_JOBS:-6}
mkdir -p "$logs" "$prefix"
export PATH="$prefix/target-tools:$PATH"
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ] || {
    echo 'This bootstrap has been configured for an Intel macOS host.' >&2; exit 1;
}
[ "$(git -C "$xtools" rev-parse HEAD)" = 7e5dec828d2197685950e4651643126e0cf13d36 ]
[ "$(git -C "$gcc" rev-parse HEAD)" = 1c613cea0091a4afea234ea3da6465370084b3ec ]
[ -f "$sdk/SDKSettings.plist" ]
for change in "$root"/scripts/toolchain-patches/gcc14-*.patch; do
    if ! patch -d "$gcc" -p1 -R --dry-run -s -f < "$change" >/dev/null 2>&1; then
        patch -d "$gcc" -p1 -F 0 --batch --forward < "$change"
    fi
done
case "${1:-}" in
xtools)
    cmake -S "$xtools" -B "$tp/build-leopard-xtools" -G "${RDN_CMAKE_GENERATOR:-Ninja}" \
        -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$(xcrun -f clang)" \
        -DCMAKE_CXX_COMPILER="$(xcrun -f clang++)" \
        -DCMAKE_OSX_SYSROOT="$(xcrun --show-sdk-path)" \
        -DXTOOLS_HOST_IS_64B=ON -DDARWIN_PREFER_PUBLIC_SDK=ON \
        -DBUILD_TESTING=OFF 2>&1 | tee "$logs/xtools-configure.log"
    cmake --build "$tp/build-leopard-xtools" --parallel "$jobs" \
        2>&1 | tee "$logs/xtools-build.log"
    cmake --install "$tp/build-leopard-xtools" \
        2>&1 | tee "$logs/xtools-install.log"
    mv "$prefix/bin/ld" "$prefix/bin/ld.real"
    cp "$root/scripts/leopard-ld-wrapper.sh" "$prefix/bin/ld"
    chmod 755 "$prefix/bin/ld"
    mkdir -p "$prefix/powerpc-apple-darwin9/bin" "$prefix/target-tools"
    for tool in as ld ar ranlib nm strip otool lipo install_name_tool; do
        ln -sfn "$tool" "$prefix/bin/powerpc-apple-darwin9-$tool"
        ln -sfn "../../bin/$tool" "$prefix/powerpc-apple-darwin9/bin/$tool"
        ln -sfn "../bin/$tool" "$prefix/target-tools/powerpc-apple-darwin9-$tool"
    done
    ln -sfn "$(xcrun -f dsymutil)" "$prefix/target-tools/powerpc-apple-darwin9-dsymutil"
    ;;
gcc-configure)
    [ -x "$prefix/bin/as" ] && [ -x "$prefix/bin/ld" ]
    mkdir -p "$tp/build-leopard-gcc"
    cd "$tp/build-leopard-gcc"
    AR_FOR_TARGET="$prefix/bin/ar" NM_FOR_TARGET="$prefix/bin/nm" \
    RANLIB_FOR_TARGET="$prefix/bin/ranlib" STRIP_FOR_TARGET="$prefix/bin/strip" \
    OTOOL_FOR_TARGET="$prefix/bin/otool" \
    "$gcc/configure" --target=powerpc-apple-darwin9 --prefix="$prefix" \
        --with-sysroot="$sdk" --with-native-system-header-dir=/usr/include \
        --with-as="$prefix/bin/as" --with-ld="$prefix/bin/ld" \
        --with-dsymutil="$(xcrun -f dsymutil)" \
        --with-gmp="$(brew --prefix gmp)" \
        --with-mpfr="$(brew --prefix mpfr)" \
        --with-mpc="$(brew --prefix libmpc)" \
        --enable-languages=c,c++,objc --disable-bootstrap --disable-nls \
        --enable-checking=release --enable-threads=posix \
        --enable-shared --enable-static --disable-libobjc --disable-libstdcxx-pch \
        --disable-libsanitizer --disable-libvtv --disable-libquadmath \
        --disable-libgomp --disable-libssp --disable-libitm \
        2>&1 | tee "$logs/gcc-configure.log"
    ;;
gcc-build)
    make -C "$tp/build-leopard-gcc" -j "$jobs" \
        AR_FOR_TARGET="$prefix/bin/ar" NM_FOR_TARGET="$prefix/bin/nm" \
        RANLIB_FOR_TARGET="$prefix/bin/ranlib" STRIP_FOR_TARGET="$prefix/bin/strip" \
        OTOOL_FOR_TARGET="$prefix/bin/otool" \
        CFLAGS_FOR_TARGET='-O2 -g0' CXXFLAGS_FOR_TARGET='-O2 -g0' \
        LIBGCC2_DEBUG_CFLAGS=-g0 \
        2>&1 | tee "$logs/gcc-build.log"
    make -C "$tp/build-leopard-gcc" install \
        2>&1 | tee "$logs/gcc-install.log"
    ;;
*) echo "usage: bash $0 xtools|gcc-configure|gcc-build" >&2; exit 1 ;;
esac
