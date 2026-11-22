#!/bin/sh
# Supply Meson's expected identification format for this exact upstream ld64.
for argument do
    if [ "$argument" = -v ]; then
        echo '@(#)PROGRAM:ld PROJECT:ld64-236.3' >&2
        break
    fi
done
exec "$(dirname "$0")/ld.real" "$@"
