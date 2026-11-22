#!/bin/bash
# Reconstruct a fresh, checksum-verified Mesa tree; never reuse an incremental tree.
set -euo pipefail
export LC_ALL=C
root=$(cd "$(dirname "$0")/.." && pwd)
archive=${1:-$root/third_party/mesa-26.2.4.tar.xz}
destination=${2:-$root/third_party/mesa-26.2.4}
expected=bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9
[ -f "$archive" ] || { echo "Missing archive: $archive" >&2; exit 1; }
[ ! -e "$destination" ] || { echo "Refusing existing destination: $destination" >&2; exit 1; }
actual=$(shasum -a 256 "$archive" | awk '{print $1}')
[ "$actual" = "$expected" ] || { echo "Mesa archive checksum mismatch" >&2; exit 1; }
mkdir -p "$(dirname "$destination")"
stage=$(mktemp -d "${destination}.prepare.XXXXXX")
echo "Preparation directory (retained on failure): $stage"
tar -xf "$archive" -C "$stage"
src=$stage/mesa-26.2.4
[ -d "$src" ] || { echo "Missing Mesa archive root" >&2; exit 1; }
# Patch 0120 modifies the fork frontend, so overlays must exist before patching.
rsync -a "$root/mesa/winsys/" "$src/src/gallium/winsys/rdn/"
rsync -a "$root/mesa/frontend/" "$src/src/gallium/frontends/rdn/"
rsync -a --exclude hw --exclude tests --exclude gld --exclude video "$root/mesa/target/" "$src/src/gallium/targets/rdn/"
rsync -a --exclude tests "$root/video/" "$src/src/gallium/targets/rdn/video/"
rsync -a "$root/hw/" "$src/src/gallium/targets/rdn/hw/"
rsync -a "$root/mesa/tests/" "$src/src/gallium/targets/rdn/tests/"
rsync -a --exclude build "$root/gld/" "$src/src/gallium/targets/rdn/gld/"
for p in "$root"/mesa/patches/*.patch; do
    echo "Applying $(basename "$p")"
    patch -d "$src" -p1 -F 0 --batch --forward --dry-run < "$p"
    patch -d "$src" -p1 -F 0 --batch --forward < "$p"
done
python3 - "$root" "$src" "$actual" <<'PY'
import hashlib, json, pathlib, subprocess, sys
root, src = map(pathlib.Path, sys.argv[1:3])
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {}
for directory in ('mesa', 'hw', 'gld', 'video'):
    for p in sorted((root / directory).rglob('*')):
        if p.is_file() and 'build' not in p.relative_to(root).parts:
            inputs[str(p.relative_to(root))] = digest(p)
manifest = dict(mesa='26.2.4', archive_sha256=sys.argv[3],
                repository_commit=subprocess.check_output(
                    ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
                patches=[str(p.relative_to(root)) for p in sorted((root/'mesa/patches').glob('*.patch'))],
                input_sha256=inputs)
(src/'radeonni-source-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
PY
mv "$src" "$destination"
rmdir "$stage"
echo "Prepared $destination"
