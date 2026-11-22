#!/bin/sh
# Explicit-path functions for a reversible executable-only GL bundle trial.
rdn_gl_names='RadeonNIGLDriver RadeonNIGLDriver1 RadeonNIGLDriver2 RadeonNIGLDriver3'
rdn_gl_regular() { [ -f "$1" ] && [ ! -L "$1" ]; }
rdn_gl_install() {
    pkg=$1 ext=$2 backup=$3 owner=$4
    [ -d "$ext" ] && [ ! -L "$ext" ] || return 1
    for name in $rdn_gl_names; do
        dir="$ext/$name.bundle/Contents/MacOS"
        [ -d "$dir" ] && [ ! -L "$dir" ] && [ ! -L "$ext/$name.bundle" ] || return 1
        rdn_gl_regular "$pkg/normal/$name" && rdn_gl_regular "$pkg/trial/$name" && rdn_gl_regular "$dir/$name" || return 1
        cmp -s "$pkg/normal/$name" "$dir/$name" || { echo "Installed $name differs from baseline." >&2; return 1; }
    done
    [ ! -e "$backup" ] && [ ! -L "$backup" ] || return 1
    mkdir -m 700 "$backup" || return 1
    for name in $rdn_gl_names; do
        cp "$ext/$name.bundle/Contents/MacOS/$name" "$backup/$name" || return 1
        cmp -s "$pkg/normal/$name" "$backup/$name" || return 1
    done
    for name in $rdn_gl_names; do
        dir="$ext/$name.bundle/Contents/MacOS"
        tmp=$(mktemp "$dir/.rdn-trial.XXXXXXXX") || return 1
        if ! cp "$pkg/trial/$name" "$tmp" || ! chmod 755 "$tmp"; then rm -f "$tmp"; return 1; fi
        if [ "$owner" != '-' ]; then
            if ! chown "$owner" "$tmp"; then rm -f "$tmp"; return 1; fi
        fi
        if ! cmp -s "$pkg/trial/$name" "$tmp"; then rm -f "$tmp"; return 1; fi
        if ! mv -f "$tmp" "$dir/$name"; then rm -f "$tmp"; echo 'Partial install: use --restore.' >&2; return 1; fi
    done
    echo "GL baseline backup: $backup"
}
rdn_gl_restore() {
    pkg=$1 ext=$2 backup=$3 owner=$4
    [ -d "$ext" ] && [ ! -L "$ext" ] && [ -d "$backup" ] && [ ! -L "$backup" ] || return 1
    for name in $rdn_gl_names; do
        dir="$ext/$name.bundle/Contents/MacOS"; target="$dir/$name"
        [ -d "$dir" ] && [ ! -L "$dir" ] && [ ! -L "$ext/$name.bundle" ] || return 1
        rdn_gl_regular "$pkg/normal/$name" && rdn_gl_regular "$pkg/trial/$name" && rdn_gl_regular "$backup/$name" || return 1
        cmp -s "$pkg/normal/$name" "$backup/$name" || { echo 'Backup differs from baseline.' >&2; return 1; }
        if [ -e "$target" ] || [ -L "$target" ]; then
            rdn_gl_regular "$target" && { cmp -s "$pkg/normal/$name" "$target" || cmp -s "$pkg/trial/$name" "$target"; } || { echo "Unexpected $name; refusing restore." >&2; return 1; }
        fi
    done
    for name in $rdn_gl_names; do
        dir="$ext/$name.bundle/Contents/MacOS"
        tmp=$(mktemp "$dir/.rdn-restore.XXXXXXXX") || return 1
        if ! cp "$backup/$name" "$tmp" || ! chmod 755 "$tmp"; then rm -f "$tmp"; return 1; fi
        if [ "$owner" != '-' ]; then
            if ! chown "$owner" "$tmp"; then rm -f "$tmp"; return 1; fi
        fi
        if ! cmp -s "$backup/$name" "$tmp" || ! mv -f "$tmp" "$dir/$name"; then rm -f "$tmp"; return 1; fi
    done
    echo "Restored GL baseline; backup retained: $backup"
}
