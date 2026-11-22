#!/usr/bin/env python3
"""Compare an SDK release to a pinned Git blob inventory without running it.

This verifies mirror consistency, not Apple authenticity. Git metadata must be
obtained separately at a pinned revision. Optional extraction omits external
symlinks and uses Python's data extraction filter.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('git_tree', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--extract', type=Path)
    parser.add_argument('--sdk-name', default='MacOSX10.5.sdk',
                        choices=('MacOSX10.5.sdk', 'MacOSX10.4u.sdk'))
    args = parser.parse_args()
    tree = json.loads(args.git_tree.read_text())
    if tree.get('truncated'):
        raise SystemExit('Refusing truncated Git inventory')
    expected = {e['path']: e for e in tree['tree'] if e['type'] != 'tree'}
    prefix = args.sdk_name
    seen, problems, external, modes = set(), [], [], []
    counts = {'files': 0, 'symlinks': 0, 'directories': 0}
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        names = set()
        for member in members:
            name = member.name.rstrip('/')
            parts = PurePosixPath(name).parts
            if not parts or parts[0] != prefix or '..' in parts or name in names:
                problems.append('unsafe or duplicate path: ' + name)
                continue
            names.add(name)
            if member.isdir():
                counts['directories'] += 1
                continue
            relative = '/'.join(parts[1:])
            seen.add(relative)
            entry = expected.get(relative)
            if member.isfile():
                counts['files'] += 1
                mode = '100755' if member.mode & 0o111 else '100644'
                digest = hashlib.sha1(b'blob ' + str(member.size).encode() + b'\0')
                with archive.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
            elif member.issym():
                counts['symlinks'] += 1
                mode = '120000'
                data = member.linkname.encode('utf-8', 'surrogateescape')
                digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data)
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), member.linkname))
                if member.linkname.startswith('/') or resolved.split('/')[0] != prefix:
                    external.append({'path': relative, 'target': member.linkname})
            else:
                problems.append('unsupported member type: ' + name)
                continue
            if not entry or entry['type'] != 'blob' or entry['sha'] != digest.hexdigest():
                problems.append('Git content mismatch or unexpected member: ' + relative)
            elif entry['mode'] != mode:
                modes.append({'path': relative, 'git': entry['mode'], 'archive': mode})
        problems.extend('missing member: ' + name for name in sorted(set(expected) - seen))
        report = {
            'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
            'git_tree_sha': tree['sha'], 'member_counts': counts,
            'git_blob_count': len(expected), 'content_matches_git': not problems,
            'problems': problems, 'mode_differences': modes,
            'external_symlinks': external,
            'apple_authentication': 'not established; comparison is within the same mirror',
            'extracted': False,
        }
        if args.extract and not problems:
            if args.extract.exists():
                raise SystemExit('Refusing existing extraction destination')
            excluded = {prefix + '/' + e['path'] for e in external}
            args.extract.mkdir(parents=True)
            archive.extractall(args.extract,
                               members=[m for m in members if m.name not in excluded],
                               filter='data')
            for item in external:
                (args.extract / prefix / item['path']).mkdir(parents=True, exist_ok=True)
            report['extracted'] = True
            report['extraction_policy'] = 'external symlinks replaced by empty directories; data filter'
            report['extraction_directory'] = str(args.extract.resolve())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
