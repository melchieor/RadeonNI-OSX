#!/bin/sh
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
case "${1:-}" in
--restore)
    [ "$#" = 2 ] || { echo 'usage: sudo sh uninstall.sh --restore BACKUP_DIRECTORY' >&2; exit 1; }
    exec /usr/bin/python -E -S "$here/manage.py" restore "$2" ;;
--remove)
    [ "$#" = 1 ] || exit 1
    exec /usr/bin/python -E -S "$here/manage.py" remove ;;
*) echo 'usage: sudo sh uninstall.sh --restore BACKUP_DIRECTORY | --remove' >&2; exit 1 ;;
esac
