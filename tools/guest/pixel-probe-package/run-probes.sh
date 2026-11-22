#!/bin/sh
# Own-process offscreen GL tests; no installation/configuration writes.
set -u
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
cd "$here" || exit 2
[ "$(uname -p)" = powerpc ] || { echo 'Run on the Power Mac G5, not the build Mac.'; exit 2; }
case "$(sw_vers -productVersion)" in 10.5.8|10.5.9) ;; *) echo 'Leopard 10.5.8/Sorbet 10.5.9 only'; exit 2;; esac
[ "$(id -u)" != 0 ] || { echo 'Run as your normal logged-in user, without sudo.'; exit 2; }
[ ! -e results ] && [ ! -e pixel-results.zip ] || { echo 'Existing results: keep them and use a fresh extracted directory.'; exit 2; }
mkdir results || exit 2
/usr/bin/sw_vers > results/environment.txt 2>&1
/usr/bin/python -E -S ./environment.py >> results/environment.txt 2>&1
trap 'echo "Interrupted. Do not retry; retain results/gpu.log and results/software.log if present."; exit 130' INT TERM
printf 'Offscreen size sweep: 64x32, 257x129, 1024x256; 47 cases per size/backend.\n'
printf 'No test window. Save work first; allow up to two minutes.\n'
: > results/process-status.txt
for shape in small odd large; do
 case "$shape" in small) suffix= ;; *) suffix=-$shape ;; esac
 for backend in gpu software; do
  case "$backend" in gpu) software=0 ;; *) software=1 ;; esac
  label=$backend$suffix
  printf 'Running %s\n' "$label"
  RDN_SOFTWARE=$software ./pixel-render-probe$suffix "$backend" "results/$label" > "results/$label.log" 2>&1
  result=$?
  printf '%s_exit=%s\n' "$label" "$result" >> results/process-status.txt
  grep -E '^(requested=|dimensions|GL_|SUMMARY|SETUP_FAIL|CASE .*FAIL|SKIP)' "results/$label.log" || true
  if [ "$result" -ge 128 ]; then echo "Abnormal exit; stop and share results/$label.log."; exit "$result"; fi
 done
done
/usr/bin/zip -qr pixel-results.zip results || exit 2
printf '\nResults saved: %s/pixel-results.zip\n' "$here"
echo 'Share this ZIP. A successful run is not proof that WindowServer rendering is correct.'
