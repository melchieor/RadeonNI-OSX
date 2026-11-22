#!/bin/sh
# Requires rdn_tree_safe from framebuffer-core.sh. All functions use explicit paths.
rdn_graphics_names='RadeonNIGA.plugin RadeonNIGLDriver.bundle RadeonNIGLDriver1.bundle RadeonNIGLDriver2.bundle RadeonNIGLDriver3.bundle'
rdn_graphics_bundle_safe() {
    dir=$1
    [ -d "$dir" ] && [ ! -L "$dir" ] || return 1
    [ -z "$(find "$dir" -type l -print)" ] || return 1
    [ -f "$dir/Contents/Info.plist" ] && [ -d "$dir/Contents/MacOS" ] || return 1
    [ "$(find "$dir" -type f -print | wc -l | tr -d ' ')" = 2 ]
}
rdn_graphics_verify_payload() {
    root=$1
    rdn_tree_safe "$root/normal/RadeonNI.kext" && rdn_tree_safe "$root/trial/RadeonNI.kext" || return 1
    for name in $rdn_graphics_names; do rdn_graphics_bundle_safe "$root/trial/$name" || return 1; done
}
rdn_graphics_install() {
    root=$1 ext=$2 backup=$3 owner=$4
    [ -d "$ext" ] && [ ! -L "$ext" ] && rdn_graphics_verify_payload "$root" || return 1
    target="$ext/RadeonNI.kext"
    rdn_tree_safe "$target" && diff -r "$root/normal/RadeonNI.kext" "$target" >/dev/null 2>&1 || { echo 'Installed engine kext differs from baseline.' >&2; return 1; }
    for name in $rdn_graphics_names; do
        [ ! -e "$ext/$name" ] && [ ! -L "$ext/$name" ] || { echo "Existing $name: refusing overwrite." >&2; return 1; }
    done
    [ ! -e "$backup" ] && [ ! -L "$backup" ] || return 1
    mkdir -m 700 "$backup" || return 1
    cp -R "$target" "$backup/RadeonNI.kext" || return 1
    diff -r "$root/normal/RadeonNI.kext" "$backup/RadeonNI.kext" >/dev/null 2>&1 || return 1
    stage=$(mktemp -d "$ext/.radeonni-graphics.XXXXXXXX") || return 1
    for name in RadeonNI.kext $rdn_graphics_names; do
        if ! cp -R "$root/trial/$name" "$stage/$name"; then rm -rf "$stage"; return 1; fi
        if [ "$owner" != '-' ]; then
            if ! chown -R "$owner" "$stage/$name"; then rm -rf "$stage"; return 1; fi
        fi
        if ! chmod -R go-w "$stage/$name" || ! diff -r "$root/trial/$name" "$stage/$name" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    done
    # A failed move leaves the verified baseline in backup for --restore.
    if ! mv "$target" "$stage/previous.kext"; then rm -rf "$stage"; return 1; fi
    if ! mv "$stage/RadeonNI.kext" "$target"; then
        mv "$stage/previous.kext" "$target" || echo "Baseline remains at $backup/RadeonNI.kext" >&2
        return 1
    fi
    for name in $rdn_graphics_names; do
        if [ -e "$ext/$name" ] || [ -L "$ext/$name" ] || ! mv "$stage/$name" "$ext/$name"; then
            echo 'Incomplete install: run --restore; backup retained.' >&2; return 1
        fi
    done
    rm -rf "$stage"
    echo "Engine baseline backup: $backup/RadeonNI.kext"
}
rdn_graphics_restore() {
    root=$1 ext=$2 backup=$3 owner=$4
    [ -d "$ext" ] && [ ! -L "$ext" ] && rdn_graphics_verify_payload "$root" || return 1
    rdn_tree_safe "$backup/RadeonNI.kext" && diff -r "$root/normal/RadeonNI.kext" "$backup/RadeonNI.kext" >/dev/null 2>&1 || { echo 'Missing or changed backup.' >&2; return 1; }
    target="$ext/RadeonNI.kext"
    if [ -e "$target" ] || [ -L "$target" ]; then
        rdn_tree_safe "$target" || return 1
        diff -r "$root/trial/RadeonNI.kext" "$target" >/dev/null 2>&1 || diff -r "$root/normal/RadeonNI.kext" "$target" >/dev/null 2>&1 || { echo 'Unexpected kext: refusing to replace.' >&2; return 1; }
    fi
    for name in $rdn_graphics_names; do
        if [ -e "$ext/$name" ] || [ -L "$ext/$name" ]; then
            rdn_graphics_bundle_safe "$ext/$name" && diff -r "$root/trial/$name" "$ext/$name" >/dev/null 2>&1 || { echo "Changed $name: refusing removal." >&2; return 1; }
        fi
    done
    stage=$(mktemp -d "$ext/.radeonni-restore.XXXXXXXX") || return 1
    if ! cp -R "$backup/RadeonNI.kext" "$stage/old.kext"; then rm -rf "$stage"; return 1; fi
    if [ "$owner" != '-' ]; then
        if ! chown -R "$owner" "$stage/old.kext"; then rm -rf "$stage"; return 1; fi
    fi
    if ! chmod -R go-w "$stage/old.kext" || ! diff -r "$root/normal/RadeonNI.kext" "$stage/old.kext" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    if [ -e "$target" ]; then mv "$target" "$stage/previous.kext" || return 1; fi
    if ! mv "$stage/old.kext" "$target"; then
        [ ! -d "$stage/previous.kext" ] || mv "$stage/previous.kext" "$target" || :
        echo "Baseline remains at $backup/RadeonNI.kext" >&2; return 1
    fi
    for name in $rdn_graphics_names; do [ ! -d "$ext/$name" ] || rm -rf "$ext/$name" || return 1; done
    rm -rf "$stage"
    echo "Restored engine baseline; backup retained: $backup/RadeonNI.kext"
}
