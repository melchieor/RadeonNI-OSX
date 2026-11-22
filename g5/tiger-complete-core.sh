#!/bin/sh
# Uses rdn_tree_safe and rdn_graphics_bundle_safe from the packaged helpers.
rdn_complete_names='RadeonNI.kext RadeonNIGA.plugin RadeonNIGLDriver.bundle RadeonNIGLDriver1.bundle RadeonNIGLDriver2.bundle RadeonNIGLDriver3.bundle'
rdn_complete_safe() {
    payload=$1
    rdn_tree_safe "$payload/RadeonNI.kext" || return 1
    for name in $rdn_complete_names; do
        [ "$name" = RadeonNI.kext ] || rdn_graphics_bundle_safe "$payload/$name" || return 1
    done
}
rdn_complete_verify_installed() {
    payload=$1 ext=$2
    [ -d "$ext" ] && [ ! -L "$ext" ] && rdn_complete_safe "$payload" || return 1
    for name in $rdn_complete_names; do
        [ -d "$ext/$name" ] && [ ! -L "$ext/$name" ] || return 1
        [ -z "$(find "$ext/$name" -type l -print)" ] || return 1
        diff -r "$payload/$name" "$ext/$name" >/dev/null 2>&1 || return 1
    done
}
rdn_complete_install() {
    payload=$1 ext=$2 backup=$3 owner=$4 identity=$5
    [ -d "$ext" ] && [ ! -L "$ext" ] && rdn_complete_safe "$payload" || return 1
    for name in $rdn_complete_names; do
        [ ! -e "$ext/$name" ] && [ ! -L "$ext/$name" ] || { echo "Existing $name: refusing installation." >&2; return 1; }
    done
    [ ! -e "$backup" ] && [ ! -L "$backup" ] || return 1
    mkdir -m 700 "$backup" || return 1
    printf '%s\n' "$identity" > "$backup/fresh-install-id" || return 1
    stage=$(mktemp -d "$ext/.radeonni-complete.XXXXXXXX") || return 1
    for name in $rdn_complete_names; do
        if ! cp -R "$payload/$name" "$stage/$name"; then rm -rf "$stage"; return 1; fi
        if [ "$owner" != '-' ]; then
            if ! chown -R "$owner" "$stage/$name"; then rm -rf "$stage"; return 1; fi
        fi
        if ! chmod -R go-w "$stage/$name" || ! diff -r "$payload/$name" "$stage/$name" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    done
    for name in $rdn_complete_names; do
        if [ -e "$ext/$name" ] || [ -L "$ext/$name" ] || ! mv "$stage/$name" "$ext/$name"; then
            echo "Partial install: use --remove; state retained at $backup." >&2; return 1
        fi
    done
    rmdir "$stage" || return 1
    echo "Fresh-install state: $backup"
}
rdn_complete_remove() {
    payload=$1 ext=$2 backup=$3 identity=$4
    [ -d "$ext" ] && [ ! -L "$ext" ] && [ -d "$backup" ] && [ ! -L "$backup" ] && rdn_complete_safe "$payload" || return 1
    [ -f "$backup/fresh-install-id" ] && [ ! -L "$backup/fresh-install-id" ] || return 1
    [ "$(cat "$backup/fresh-install-id")" = "$identity" ] || return 1
    # Verify every existing path before removing any; missing paths are allowed
    # to recover from a partially completed fresh installation.
    for name in $rdn_complete_names; do
        if [ -e "$ext/$name" ] || [ -L "$ext/$name" ]; then
            [ -d "$ext/$name" ] && [ ! -L "$ext/$name" ] && [ -z "$(find "$ext/$name" -type l -print)" ] || return 1
            diff -r "$payload/$name" "$ext/$name" >/dev/null 2>&1 || { echo "Changed $name: refusing removal." >&2; return 1; }
        fi
    done
    for name in $rdn_complete_names; do [ ! -d "$ext/$name" ] || rm -rf "$ext/$name" || return 1; done
    echo "Fresh install removed; state retained at $backup"
}
