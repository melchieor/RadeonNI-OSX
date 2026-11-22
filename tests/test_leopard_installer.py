"""Exercise package integrity and rollback using temporary directories only."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import os
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manager',ROOT/'g5/leopard-v7900-manage.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class InstallerTests(unittest.TestCase):
    def test_settings_searchable_backups_private_under_restrictive_umask(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings=Path(temporary)/'RadeonNI'
            old=os.umask(0o077)
            try:
                manager.prepare_settings_directory(str(settings))
            finally:
                os.umask(old)
            self.assertEqual(settings.stat().st_mode & 0o777,0o711)
            self.assertEqual((settings/'Backups').stat().st_mode & 0o777,0o700)
            backup=settings/'Backups'/'existing';backup.mkdir(mode=0o700)
            manager.prepare_settings_directory(str(settings))
            self.assertEqual(backup.stat().st_mode & 0o777,0o700)
            self.assertEqual((settings/'Backups').stat().st_mode & 0o777,0o700)
    def test_settings_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);destination=root/'destination';destination.mkdir(mode=0o700)
            settings=root/'settings';settings.symlink_to(destination)
            with self.assertRaises(ValueError):manager.prepare_settings_directory(str(settings))
            self.assertEqual(destination.stat().st_mode & 0o777,0o700)

    def fixture(self, root):
        package, extensions, backup = root/'package', root/'extensions', root/'backup'
        extensions.mkdir()
        entries = {}
        for name in manager.BUNDLES:
            path = package/'payload'/name/'Contents/MacOS/test'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'new driver')
            entries[str(path.relative_to(package))] = manager.digest(str(path))
        manager.write_plist(entries,str(package/'MANIFEST.plist'))
        old = extensions/manager.BUNDLES[0]/'Contents/MacOS/test'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'previous driver')
        return package, extensions, backup

    def test_install_restore_and_previously_absent_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            package, extensions, backup = self.fixture(Path(temporary))
            manager.install(str(package),str(extensions),str(backup))
            self.assertEqual((extensions/manager.BUNDLES[0]/'Contents/MacOS/test').read_bytes(), b'new driver')
            manager.restore(str(extensions),str(backup))
            self.assertEqual((extensions/manager.BUNDLES[0]/'Contents/MacOS/test').read_bytes(), b'previous driver')
            self.assertFalse((extensions/manager.BUNDLES[1]).exists())

    def test_settings_initialized_only_after_package_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);package,extensions,unused=self.fixture(root)
            settings=root/'RadeonNI';backup=settings/'Backups'/'test'
            payload=package/'payload'/manager.BUNDLES[0]/'Contents/MacOS/test'
            payload.write_bytes(b'bad')
            with self.assertRaises(ValueError):manager.install(str(package),str(extensions),str(backup),str(settings))
            self.assertFalse(settings.exists())
            payload.write_bytes(b'new driver')
            manager.install(str(package),str(extensions),str(backup),str(settings))
            self.assertEqual(settings.stat().st_mode & 0o111,0o111)
            self.assertEqual((settings/'Backups').stat().st_mode & 0o777,0o700)
            self.assertEqual(backup.stat().st_mode & 0o777,0o700)

    def test_failed_install_rolls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            package, extensions, backup = self.fixture(Path(temporary))
            original = manager.copy_bundle
            calls = [0]
            def injected_failure(source, destination):
                calls[0] += 1
                if calls[0] == 3:
                    raise OSError('simulated write failure')
                return original(source,destination)
            manager.copy_bundle = injected_failure
            try:
                with self.assertRaises(OSError):
                    manager.install(str(package),str(extensions),str(backup))
            finally:
                manager.copy_bundle = original
            self.assertEqual((extensions/manager.BUNDLES[0]/'Contents/MacOS/test').read_bytes(), b'previous driver')
            for name in manager.BUNDLES[1:]:
                self.assertFalse((extensions/name).exists())

    def test_corrupt_payload_rejected_before_backup_or_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            package, extensions, backup = self.fixture(Path(temporary))
            (package/'payload'/manager.BUNDLES[0]/'Contents/MacOS/test').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                manager.install(str(package),str(extensions),str(backup))
            self.assertFalse(backup.exists())
            self.assertEqual((extensions/manager.BUNDLES[0]/'Contents/MacOS/test').read_bytes(), b'previous driver')

    def test_corrupt_backup_rejected_before_changing_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            package, extensions, backup = self.fixture(Path(temporary))
            manager.install(str(package),str(extensions),str(backup))
            (backup/manager.BUNDLES[0]/'Contents/MacOS/test').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                manager.restore(str(extensions),str(backup))
            self.assertEqual((extensions/manager.BUNDLES[0]/'Contents/MacOS/test').read_bytes(), b'new driver')

    def test_unexpected_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            package, extensions, backup = self.fixture(Path(temporary))
            extra = package/'extra'
            extra.write_bytes(b'not in manifest')
            with self.assertRaises(ValueError):
                manager.verify(str(package))
            extra.unlink()
            extra.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                manager.verify(str(package))


class InstallerShellTests(unittest.TestCase):
    def run_installer(self, mode, present=False, loadable=True, version='10.5.8', diagnostic_error=False, symbols=True):
        # Rewrite only the test copy's fixed command paths; every privileged
        # command is a stub. Never execute the real installer on this host.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commands = root/'bin'
            commands.mkdir()
            log = root/'calls'
            stubs = {
                'uname': 'echo powerpc', 'sw_vers': 'echo '+version,
                'id': 'echo 0', 'python': 'echo "python $*" >> "$CALLS"',
                'ioreg': 'echo ioreg >> "$CALLS"; echo '+('pci1002,6704' if present else 'pci10de,0092'),
                 'kextload': ('echo "kextload $*" >> "$CALLS"; '
                    + ('echo "RadeonNIAccel is not compatible with its superclass"; ' if diagnostic_error else '')
                    + ('while [ "$#" -gt 0 ]; do if [ "$1" = -s ]; then shift; echo linked > "$1/org.osxgpu.driver.RadeonNI.sym"; fi; shift; done; ' if symbols else '')
                    + 'exit '+('0' if loadable else '1')),
                'cp': ':', 'chown': ':', 'chmod': ':'}
            for name, body in stubs.items():
                path = commands/name
                path.write_text('#!/bin/sh\n'+body+'\n')
                path.chmod(0o755)
            source = (ROOT/'g5/leopard-v7900-install.sh').read_text()
            source = source.replace('PATH=/bin:/sbin:/usr/bin:/usr/sbin',
                                    'PATH="'+str(commands)+':/bin:/usr/bin"')
            source = source.replace('/usr/bin/python',str(commands/'python'))
            script = root/'install.sh'
            script.write_text(source)
            result = subprocess.run(['/bin/sh',str(script),mode],
                                    env=dict(os.environ,CALLS=str(log)),
                                    capture_output=True,text=True)
            return result, log.read_text() if log.exists() else ''

    def test_prepare_swap_without_amd_checks_then_installs(self):
        result, calls = self.run_installer('--prepare-swap')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('ioreg',calls)
        self.assertIn('kextload',calls)
        self.assertTrue(calls.rstrip().endswith('manage.py install'))
        self.assertLess(calls.index('kextload'),calls.index('manage.py install'))

    def test_normal_modes_still_require_amd(self):
        for mode in ('--check','--install'):
            result, calls = self.run_installer(mode)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('kextload',calls)
            self.assertNotIn('manage.py install',calls)

    def test_failed_loadability_prevents_swap_install(self):
        result, calls = self.run_installer('--prepare-swap',loadable=False)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('manage.py install',calls)

    def test_tiger_still_rejected(self):
        result, calls = self.run_installer('--prepare-swap',version='10.4.11')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(calls,'')

    def test_check_with_amd_does_not_install(self):
        result, calls = self.run_installer('--check',present=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('kextload',calls)
        self.assertNotIn('manage.py install',calls)

    def test_check_before_swap_links_without_installing(self):
        result, calls = self.run_installer('--check-before-swap')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('ioreg',calls)
        self.assertIn('kextload -t -n -v 6 -s',calls)
        self.assertNotIn('manage.py install',calls)

    def test_zero_exit_with_abi_diagnostic_still_rejected(self):
        result, calls = self.run_installer('--prepare-swap',diagnostic_error=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('manage.py install',calls)

    def test_missing_link_output_rejected(self):
        result, calls = self.run_installer('--prepare-swap',symbols=False)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('manage.py install',calls)


if __name__ == '__main__':
    unittest.main()
