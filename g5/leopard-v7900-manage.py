#!/usr/bin/python
"""Leopard Python 2.5 compatible integrity checks and reversible installation."""
import sys
# Do not import modules supplied beside an unpacked package before verification.
if sys.path:
    del sys.path[0]
sys.path = [entry for entry in sys.path if entry]
import hashlib
import os
import plistlib
import shutil
import stat
import time

BUNDLES = ['RadeonNI.kext', 'RadeonNIGA.plugin'] + [
    'RadeonNIGLDriver' + suffix + '.bundle' for suffix in ('', '1', '2', '3')]


def read_plist(path):
    if hasattr(plistlib, 'readPlist'):
        return plistlib.readPlist(path)
    stream = open(path, 'rb')
    try:
        return plistlib.load(stream)
    finally:
        stream.close()


def write_plist(value, path):
    if hasattr(plistlib, 'writePlist'):
        plistlib.writePlist(value, path)
        return
    stream = open(path, 'wb')
    try:
        plistlib.dump(value, stream)
    finally:
        stream.close()


def digest(path):
    result = hashlib.sha256()
    stream = open(path, 'rb')
    try:
        while True:
            data = stream.read(1024 * 1024)
            if not data:
                break
            result.update(data)
    finally:
        stream.close()
    return result.hexdigest()


def verify(package):
    package = os.path.realpath(package)
    entries = read_plist(os.path.join(package, 'MANIFEST.plist'))
    expected = set(entries)
    actual = set()
    for directory, dirs, files in os.walk(package):
        for name in dirs + files:
            if os.path.islink(os.path.join(directory, name)):
                raise ValueError('symbolic links are not permitted in this package')
        for name in files:
            path = os.path.join(directory, name)
            relative = path[len(package) + 1:]
            if relative not in ('MANIFEST.plist', '.DS_Store') and name != '.DS_Store':
                actual.add(relative)
    if actual != expected:
        raise ValueError('package has missing or unexpected files')
    for name, checksum in entries.items():
        path = os.path.realpath(os.path.join(package, name))
        if not path.startswith(package + os.sep) or digest(path) != checksum:
            raise ValueError('checksum/path verification failed: ' + name)
    return len(entries)


def remove_path(path):
    if os.path.islink(path):
        raise ValueError('refusing extension symlink: ' + path)
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        raise ValueError('expected a bundle directory: ' + path)


def copy_bundle(source, destination):
    shutil.copytree(source, destination)
    for directory, dirs, files in os.walk(destination):
        os.chmod(directory, int('755', 8))
        for name in files:
            path = os.path.join(directory, name)
            mode = '755' if os.sep + 'MacOS' + os.sep in path else '644'
            os.chmod(path, int(mode, 8))


def restore(extensions, backup):
    state = read_plist(os.path.join(backup, 'state.plist'))
    if state.get('format') != 1 or set(state['previous']) != set(BUNDLES):
        raise ValueError('not a RadeonNI V7900 backup')
    for name, checksum in state['checksums'].items():
        path = os.path.realpath(os.path.join(backup, name))
        if not path.startswith(os.path.realpath(backup) + os.sep) or digest(path) != checksum:
            raise ValueError('backup checksum/path mismatch: ' + name)
    # Check every backup before changing any installed file.
    for name in BUNDLES:
        if state['previous'][name] and not os.path.isdir(os.path.join(backup, name)):
            raise ValueError('incomplete backup: ' + name)
    for name in BUNDLES:
        destination = os.path.join(extensions, name)
        remove_path(destination)
        if state['previous'][name]:
            copy_bundle(os.path.join(backup, name), destination)


def install(package, extensions, backup, settings=None):
    verify(package)
    if os.path.exists(backup):
        raise ValueError('backup already exists')
    if settings is not None:
        prepare_settings_directory(settings)
    os.makedirs(backup, int('700', 8))
    previous = {}
    for name in BUNDLES:
        path = os.path.join(extensions, name)
        if os.path.islink(path) or (os.path.exists(path) and not os.path.isdir(path)):
            raise ValueError('unexpected installed bundle: ' + name)
        previous[name] = os.path.isdir(path)
        if previous[name]:
            shutil.copytree(path, os.path.join(backup, name))
    checksums = {}
    for directory, dirs, files in os.walk(backup):
        for name in files:
            path = os.path.join(directory, name)
            checksums[path[len(backup) + 1:]] = digest(path)
    write_plist(dict(format=1, previous=previous, checksums=checksums), os.path.join(backup, 'state.plist'))
    try:
        for name in BUNDLES:
            remove_path(os.path.join(extensions, name))
            copy_bundle(os.path.join(package, 'payload', name), os.path.join(extensions, name))
    except:
        restore(extensions, backup)
        raise


def host_guard():
    import platform
    if platform.machine() not in ('Power Macintosh', 'ppc', 'ppc64'):
        raise ValueError('installation/removal is restricted to the Power Mac')
    if platform.mac_ver()[0] not in ('10.5.8', '10.5.9'):
        raise ValueError('requires Leopard 10.5.8 or Sorbet 10.5.9')
    if os.geteuid() != 0:
        raise ValueError('run through sudo')


def refresh_cache(extensions):
    # Never unload the running graphics stack or restart WindowServer.
    for path in ('/System/Library/Extensions.mkext', '/System/Library/Extensions.kextcache'):
        if os.path.isfile(path):
            os.unlink(path)
    os.utime(extensions, None)


def prepare_settings_directory(settings):
    # The GL bundles inspect opt-outs as non-root processes. Backup creation
    # with mode 0700 must not make the shared settings parent unsearchable.
    if os.path.lexists(settings):
        if os.path.islink(settings) or not os.path.isdir(settings):
            raise ValueError('unexpected RadeonNI settings path')
    else:
        os.mkdir(settings, int('700', 8))
    mode = stat.S_IMODE(os.stat(settings).st_mode)
    os.chmod(settings, mode | int('111', 8))
    backups = os.path.join(settings, 'Backups')
    if os.path.lexists(backups):
        if os.path.islink(backups) or not os.path.isdir(backups):
            raise ValueError('unexpected RadeonNI backups path')
    else:
        os.mkdir(backups, int('700', 8))


def main():
    package = os.path.dirname(os.path.realpath(__file__))
    if len(sys.argv) == 2 and sys.argv[1] == 'verify':
        sys.stdout.write('Verified %d package files.\n' % verify(package))
        return
    host_guard()
    extensions = '/System/Library/Extensions'
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    if action == 'install' and len(sys.argv) == 2:
        settings = '/Library/Application Support/RadeonNI'
        backup = settings + '/Backups/V7900-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
        install(package, extensions, backup, settings)
        sys.stdout.write('Installed. Backup: ' + backup + '\n')
    elif action == 'restore' and len(sys.argv) == 3:
        restore(extensions, os.path.realpath(sys.argv[2]))
        sys.stdout.write('Previous driver files restored.\n')
    elif action == 'remove' and len(sys.argv) == 2:
        for name in BUNDLES:
            remove_path(os.path.join(extensions, name))
        sys.stdout.write('RadeonNI package components removed; backups retained.\n')
    else:
        raise ValueError('invalid management command')
    refresh_cache(extensions)
    sys.stdout.write('Restart when ready; the running driver has not been unloaded.\n')


if __name__ == '__main__':
    try:
        main()
    except:
        sys.stderr.write('RadeonNI: ' + str(sys.exc_info()[1]) + '\n')
        sys.exit(1)
