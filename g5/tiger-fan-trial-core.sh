#!/bin/sh
# Depends on rdn_tree_safe from tiger-framebuffer-core.sh.
rdn_fan_install() {
    normal=$1 trial=$2 ext=$3 backup=$4 owner=$5
    target="$ext/RadeonNI.kext"
    [ -d "$ext" ] && [ ! -L "$ext" ] || return 1
    rdn_tree_safe "$normal" && rdn_tree_safe "$trial" && rdn_tree_safe "$target" || return 1
    diff -r "$normal" "$target" >/dev/null 2>&1 || { echo 'Installed kext differs from baseline.' >&2; return 1; }
    [ ! -e "$backup" ] && [ ! -L "$backup" ] || { echo 'Backup already exists.' >&2; return 1; }
    mkdir -m 700 "$backup" || return 1
    cp -R "$target" "$backup/RadeonNI.kext" || return 1
    rdn_tree_safe "$backup/RadeonNI.kext" && diff -r "$normal" "$backup/RadeonNI.kext" >/dev/null 2>&1 || return 1
    stage=$(mktemp -d "$ext/.radeonni-fan.XXXXXXXX") || return 1
    if ! cp -R "$trial" "$stage/new.kext"; then rm -rf "$stage"; return 1; fi
    if [ "$owner" != '-' ]; then
        if ! chown -R "$owner" "$stage/new.kext"; then rm -rf "$stage"; return 1; fi
    fi
    if ! chmod -R go-w "$stage/new.kext" || ! diff -r "$trial" "$stage/new.kext" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    if ! mv "$target" "$stage/previous.kext"; then rm -rf "$stage"; return 1; fi
    if ! mv "$stage/new.kext" "$target"; then
        mv "$stage/previous.kext" "$target" || echo "Restore manually from $backup/RadeonNI.kext" >&2
        return 1
    fi
    rm -rf "$stage"
    echo "Baseline backup: $backup/RadeonNI.kext"
}

rdn_fan_restore() {
    normal=$1 trial=$2 ext=$3 backup=$4 owner=$5
    target="$ext/RadeonNI.kext"
    [ -d "$ext" ] && [ ! -L "$ext" ] || return 1
    rdn_tree_safe "$normal" && rdn_tree_safe "$trial" && rdn_tree_safe "$backup/RadeonNI.kext" || return 1
    diff -r "$normal" "$backup/RadeonNI.kext" >/dev/null 2>&1 || { echo 'Backup does not match baseline.' >&2; return 1; }
    if [ -e "$target" ] || [ -L "$target" ]; then
        rdn_tree_safe "$target" && diff -r "$trial" "$target" >/dev/null 2>&1 || { echo 'Installed kext differs from trial; refusing to replace.' >&2; return 1; }
    fi
    stage=$(mktemp -d "$ext/.radeonni-restore.XXXXXXXX") || return 1
    if ! cp -R "$backup/RadeonNI.kext" "$stage/old.kext"; then rm -rf "$stage"; return 1; fi
    if [ "$owner" != '-' ]; then
        if ! chown -R "$owner" "$stage/old.kext"; then rm -rf "$stage"; return 1; fi
    fi
    if ! chmod -R go-w "$stage/old.kext" || ! diff -r "$normal" "$stage/old.kext" >/dev/null 2>&1; then rm -rf "$stage"; return 1; fi
    if [ -e "$target" ]; then
        if ! mv "$target" "$stage/trial.kext"; then rm -rf "$stage"; return 1; fi
    fi
    if ! mv "$stage/old.kext" "$target"; then
        [ ! -d "$stage/trial.kext" ] || mv "$stage/trial.kext" "$target" || :
        echo "Restore manually from $backup/RadeonNI.kext" >&2; return 1
    fi
    rm -rf "$stage"
    echo "Restored baseline; backup retained at $backup/RadeonNI.kext"
}
