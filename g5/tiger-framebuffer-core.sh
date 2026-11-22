#!/bin/sh
# Functions only. Callers provide explicit disposable or system paths.
rdn_tree_safe() {
    [ -d "$1" ] && [ ! -L "$1" ] || return 1
    [ -z "$(find "$1" -type l -print)" ] || return 1
    [ -f "$1/Contents/Info.plist" ] && [ -f "$1/Contents/MacOS/RadeonNI" ] || return 1
    [ "$(find "$1" -type f -print | wc -l | tr -d ' ')" = 2 ] || return 1
}

rdn_install() {
    source_bundle=$1 extension_dir=$2 owner=$3
    [ -d "$extension_dir" ] && [ ! -L "$extension_dir" ] || return 1
    rdn_tree_safe "$source_bundle" || return 1
    target="$extension_dir/RadeonNI.kext"
    [ ! -e "$target" ] && [ ! -L "$target" ] || { echo 'Existing RadeonNI.kext: refusing to overwrite.' >&2; return 1; }
    stage=$(mktemp -d "$extension_dir/.radeonni-stage.XXXXXXXX") || return 1
    if ! cp -R "$source_bundle" "$stage/RadeonNI.kext"; then rm -rf "$stage"; return 1; fi
    if [ "$owner" != '-' ]; then
        if ! chown -R "$owner" "$stage/RadeonNI.kext"; then rm -rf "$stage"; return 1; fi
    fi
    if ! chmod -R go-w "$stage/RadeonNI.kext" || ! rdn_tree_safe "$stage/RadeonNI.kext"; then rm -rf "$stage"; return 1; fi
    if ! diff -r "$source_bundle" "$stage/RadeonNI.kext" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    if [ -e "$target" ] || [ -L "$target" ]; then rm -rf "$stage"; return 1; fi
    if ! mv "$stage/RadeonNI.kext" "$target"; then rm -rf "$stage"; return 1; fi
    rmdir "$stage" || return 1
}

rdn_remove() {
    source_bundle=$1 extension_dir=$2
    [ -d "$extension_dir" ] && [ ! -L "$extension_dir" ] || return 1
    target="$extension_dir/RadeonNI.kext"
    rdn_tree_safe "$source_bundle" && rdn_tree_safe "$target" || return 1
    if ! diff -r "$source_bundle" "$target" >/dev/null 2>&1; then
        echo 'Installed bundle differs from this package: refusing removal.' >&2
        return 1
    fi
    rm -rf "$target"
}
