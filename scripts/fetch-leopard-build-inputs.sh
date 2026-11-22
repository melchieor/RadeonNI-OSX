#!/bin/bash
# Fetch pinned sources into third_party; never install system packages.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
tp=$root/third_party
mkdir -p "$tp" "$root/build/leopard-v7900/sdk-audit"
fetch_git() {
    url=$1 directory=$2 revision=$3
    if [ ! -d "$directory/.git" ]; then
        git clone --depth 1 --filter=blob:none --no-checkout "$url" "$directory"
    fi
    if ! git -C "$directory" cat-file -e "$revision^{commit}" 2>/dev/null; then
        git -C "$directory" fetch --depth 1 origin "$revision"
    fi
    if [ "$(basename "$directory")" = linux-firmware ]; then
        git -C "$directory" sparse-checkout set --no-cone \
            /radeon/CAYMAN_pfp.bin /radeon/CAYMAN_me.bin /radeon/CAYMAN_mc.bin \
            /radeon/CAYMAN_rlc.bin /radeon/CAYMAN_smc.bin /LICENSES/LICENSE.radeon /WHENCE
    fi
    # A fresh --no-checkout clone still needs its worktree populated.
    if [ ! -f "$directory/.radeonni-pinned" ]; then
        git -C "$directory" checkout --detach "$revision"
        printf '%s\n' "$revision" > "$directory/.radeonni-pinned"
    fi
    [ "$(git -C "$directory" rev-parse HEAD)" = "$revision" ]
}
download() {
    url=$1 path=$2 expected=$3
    if [ ! -f "$path" ]; then
        curl --fail --location --retry 2 "$url" -o "$path.partial"
        mv "$path.partial" "$path"
    fi
    [ "$(shasum -a 256 "$path" | awk '{print $1}')" = "$expected" ] || {
        echo "Checksum mismatch: $path" >&2; exit 1;
    }
}
fetch_git https://github.com/iains/darwin-xtools.git "$tp/darwin-xtools" 7e5dec828d2197685950e4651643126e0cf13d36
fetch_git https://github.com/iains/gcc-14-branch.git "$tp/gcc-14-darwin" 1c613cea0091a4afea234ea3da6465370084b3ec
fetch_git https://gitlab.com/kernel-firmware/linux-firmware.git "$tp/linux-firmware" 69e51bb26f3fa3e118dd770f1962a93bed690dc1
download https://archive.mesa3d.org/mesa-26.2.4.tar.xz "$tp/mesa-26.2.4.tar.xz" bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9
download https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz "$tp/bison-3.8.2.tar.xz" 9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2
mkdir -p "$tp/sdk-audit"
download https://github.com/phracker/MacOSX-SDKs/releases/download/11.3/MacOSX10.5.sdk.tar.xz \
    "$tp/sdk-audit/MacOSX10.5.sdk.tar.xz" 3970800422a5e22122b92e7ce2f30513714272e4cd9096e551b8bd27466e3c2b
inventory=$root/build/leopard-v7900/sdk-audit/git-tree.json
if [ ! -f "$inventory" ]; then
    curl --fail --location \
        'https://api.github.com/repos/phracker/MacOSX-SDKs/git/trees/d2a55160a7f9ab364fe045e70ef5195dc1bdedc7?recursive=1' \
        -o "$inventory"
fi
if [ ! -d "$tp/sdk-audit/extracted" ]; then
    python3 "$root/scripts/verify-leopard-sdk.py" "$tp/sdk-audit/MacOSX10.5.sdk.tar.xz" \
        "$inventory" "$root/build/leopard-v7900/sdk-audit/archive-verification.json" \
        --extract "$tp/sdk-audit/extracted"
fi
python3 "$root/scripts/stage-cayman-firmware.py"
