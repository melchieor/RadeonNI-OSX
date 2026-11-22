#!/bin/sh
# Launch only the requested CFM game, with an isolated threading setting.
set -u
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
case "${1:-}" in
    unreal) dir='/Volumes/Data/Games/OSX/Unreal'; app='Unreal OS X' ;;
    tournament) dir='/Volumes/Data/Games/OSX/Unreal Tournament'; app='Unreal Tournament OS X' ;;
    *) echo 'Usage: sh ./cfm-game-test.sh unreal|tournament [serial|threaded]' >&2; exit 2 ;;
esac
case "${2:-serial}" in serial) RDN_GLTHREAD=0 ;; threaded) RDN_GLTHREAD=1 ;; *) exit 2 ;; esac
[ "$#" -le 2 ] || exit 2
[ -f "$dir/$app" ] || { echo "Game executable not found: $dir/$app" >&2; exit 1; }
cd "$dir" || exit 1
tag="$(date '+%Y%m%d-%H%M%S')-$$"
RDN_SOFTWARE=0
RDN_GLD_LOG="$HOME/Desktop/radeon-cfm-$tag-gld.log"
log="$HOME/Desktop/radeon-cfm-$tag-output.txt"
export RDN_GLTHREAD RDN_SOFTWARE RDN_GLD_LOG
echo "GL driver log: $RDN_GLD_LOG"
echo "Game output: $log"
echo 'Launching the game. Quit it normally or report any crash.'
/System/Library/Frameworks/Carbon.framework/Versions/A/Support/LaunchCFMApp "./$app" > "$log" 2>&1
status=$?
echo "game_exit_status=$status"
echo "GL driver log: $RDN_GLD_LOG"
echo "Game output: $log"
exit "$status"
