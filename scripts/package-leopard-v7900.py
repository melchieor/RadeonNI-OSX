#!/usr/bin/env python3
"""Assemble the validated, self-contained V7900 controlled-test ZIP."""
import hashlib
import datetime
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'build/leopard-v7900'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def qe_profile(template, firmware_dir):
    spec = importlib.util.spec_from_file_location('profiles',ROOT/'scripts/configure-device-families.py')
    profiles = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profiles)
    info = profiles.configure(template,['CAYMAN'],firmware_dir)
    profile = info['IOKitPersonalities']['RadeonNI-CAYMAN']
    profile['IOPCIMatch'] = '0x67041002'
    profile['TemperatureFanControl'] = True
    # Keep the gate: permit the existing GPU-backed compositor path only.
    profile['BackingSurfaces'] = True
    profile['HWCursor'] = True
    profile['EnableSleepRehearsal'] = True
    info['IOKitPersonalities'] = {'RadeonNI-V7900':profile}
    return info


def main():
    subprocess.run([sys.executable,str(ROOT/'scripts/validate-leopard-build.py')],check=True)
    validation = json.loads((BUILD/'validation.json').read_text())
    if not validation['passed']:
        raise SystemExit('Static validation has not passed')
    revision = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    branch = subprocess.check_output(['git','-C',str(ROOT),'symbolic-ref','--short','HEAD'],text=True).strip()
    dirty = subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True)
    if dirty:
        raise SystemExit('Commit the reviewed source before making the delivery archive')
    package_date = os.environ.get('RDN_PACKAGE_DATE','20261110')
    archive_date = datetime.datetime.strptime(package_date,'%Y%m%d').timetuple()[:6]
    name = 'RadeonNI-Leopard-V7900-'+package_date+'-'+revision[:8]
    stage = BUILD/'distribution'/name
    if stage.exists():
        shutil.rmtree(stage)
    payload = stage/'payload'
    payload.mkdir(parents=True)
    shutil.copytree(BUILD/'kernel-final/RadeonNI.kext',payload/'RadeonNI.kext')
    shutil.copytree(BUILD/'ga-final/RadeonNIGA.plugin',payload/'RadeonNIGA.plugin')
    for source,destination in [
        (BUILD/'kernel-final/RadeonNI.kext/Contents/MacOS/RadeonNI',payload/'RadeonNI.kext/Contents/MacOS/RadeonNI'),
        (BUILD/'ga-final/RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA',payload/'RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA')]:
        if checksum(source) != checksum(destination):
            raise ValueError('staged binary differs from validated input')
    info_path = payload/'RadeonNI.kext/Contents/Info.plist'
    info = qe_profile(plistlib.loads(info_path.read_bytes()), ROOT/'firmware')
    info_path.write_bytes(plistlib.dumps(info,sort_keys=False))
    base = plistlib.loads((ROOT/'gld/Info.plist').read_bytes())
    for suffix in ('','1','2','3'):
        module = 'RadeonNIGLDriver'+suffix
        contents = payload/(module+'.bundle')/'Contents'
        (contents/'MacOS').mkdir(parents=True)
        meta = dict(base,CFBundleExecutable=module,CFBundleName=module,
                    CFBundleIdentifier=base['CFBundleIdentifier']+suffix)
        (contents/'Info.plist').write_bytes(plistlib.dumps(meta))
        shutil.copy2(BUILD/'universal'/module,contents/'MacOS'/module)
        if checksum(BUILD/'universal'/module) != checksum(contents/'MacOS'/module):
            raise ValueError('staged GL module differs from validated input')
    for source,destination in [('leopard-v7900-install.sh','install.sh'),
                               ('leopard-v7900-uninstall.sh','uninstall.sh'),
                               ('leopard-v7900-manage.py','manage.py'),
                               ('LEOPARD-V7900-INSTALL.txt','INSTALL.txt')]:
        shutil.copy2(ROOT/'g5'/source,stage/destination)
    shutil.copy2(BUILD/'validation.json',stage/'validation.json')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-BACKING-COMPLETION-TRIAL.md',stage/'RENDERING-TEST.txt')
    shutil.copy2(BUILD/'fan-monitor',stage/'fan-monitor')
    shutil.copy2(BUILD/'sleep-rehearsal',stage/'sleep-rehearsal')
    shutil.copy2(BUILD/'maintenance-rehearsal',stage/'maintenance-rehearsal')
    shutil.copy2(BUILD/'resource-rehearsal',stage/'resource-rehearsal')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-SLEEP-STAGE3.md',stage/'SLEEP-STAGE3.txt')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-SLEEP-STAGE2.md',stage/'SLEEP-STAGE2.txt')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-SLEEP-STAGE1.md',stage/'SLEEP-STAGE1.txt')
    shutil.copytree(BUILD/'qe-probes',stage/'diagnostics-tools')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-QE.md',stage/'QE-TEST.txt')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-CURSOR.md',stage/'CURSOR-TEST.txt')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-FAN.md',stage/'FAN-UPDATE.txt')
    shutil.copy2(ROOT/'LICENSE',stage/'LICENSE')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-REPRODUCE.md',stage/'REPRODUCE.md')
    shutil.copy2(ROOT/'docs/LEOPARD-V7900-ABI-INVESTIGATION.md',stage/'ABI-INVESTIGATION.md')
    licenses = stage/'licenses'
    licenses.mkdir()
    mesa = ROOT/'third_party/mesa-26.2.4'
    shutil.copy2(mesa/'docs/license.rst',licenses/'LICENSE.mesa')
    shutil.copytree(mesa/'licenses',licenses/'mesa')
    for source,destination in [('COPYING3','GPL-3.0.txt'),('COPYING.RUNTIME','GCC-RUNTIME-EXCEPTION.txt')]:
        shutil.copy2(ROOT/'third_party/gcc-14-darwin'/source,licenses/destination)
    firmware = stage/'firmware'
    firmware.mkdir()
    firmware_manifest = json.loads((ROOT/'firmware/cayman-manifest.json').read_text())
    expected_firmware = {'CAYMAN_pfp.bin','CAYMAN_me.bin','CAYMAN_mc.bin',
                         'CAYMAN_rlc.bin','CAYMAN_smc.bin','LICENSE.radeon'}
    if set(firmware_manifest['files']) != expected_firmware:
        raise ValueError('unexpected firmware inventory')
    for name_ in sorted(expected_firmware):
        source = ROOT/'firmware'/name_
        if checksum(source) != firmware_manifest['files'][name_]['sha256']:
            raise ValueError('firmware checksum mismatch')
        shutil.copy2(source,firmware/name_)
    shutil.copy2(ROOT/'firmware/cayman-manifest.json',firmware/'cayman-manifest.json')
    shutil.copytree(BUILD/'logs',stage/'build-logs')
    diagnostics = stage/'diagnostics'
    diagnostics.mkdir()
    shutil.copy2(BUILD/'universal/manifest.json',diagnostics/'universal-manifest.json')
    for report in ('compiler-abi-validation.json','gcc14-abi-rejection.json'):
        shutil.copy2(BUILD/report,diagnostics/report)
    for name_ in ('archive-verification.json','apple-header-comparison.json','provenance.json','git-tree.json'):
        shutil.copy2(BUILD/'sdk-audit'/name_,diagnostics/name_)
    shutil.copy2(ROOT/'third_party/mesa-26.2.4/radeonni-source-manifest.json',diagnostics/'mesa-source-manifest.json')
    subprocess.run(['git','-C',str(ROOT),'bundle','create',str(stage/'SOURCE.bundle'),
                    'refs/heads/'+branch],check=True)
    historical = BUILD/'previous-kernel-abi-rejection.json'
    if historical.exists():
        shutil.copy2(historical,diagnostics/historical.name)
    reference = ROOT/'third_party/apple-leopard-update/reference'
    reference_hashes = {str(path.relative_to(reference)):checksum(path)
                        for path in reference.rglob('*') if path.is_file() and not path.is_symlink()}
    provenance = dict(source_commit=revision,branch=branch,
                      target_pci='1002:6704',target_os=['10.5.8','10.5.9'],build_host='Intel macOS',
                      kernel='PPC32',ga='PPC32',gl='four bundles, each PPC32 + PPC64',
                      hardware_tested=False,native_leopard_load_tested=False,
                      previous_build_failed_native_abi=True,
                      fan_control='40%-minimum temperature/RPM trial; rejoins established curve at 55 C',
                      qe_change='BackingSurfaces=true; SurfaceGate remains true; user confirmed QE on 01df8ecd',
                      cursor_change='tested 7527fc44 cursor implementation retained; no new cursor changes',
                      rendering_change='opt-in WindowServer GPU-backing alias bypass via existing checked import; prior pixel-store correction retained; native result pending',
                      gl_build_mode='isolated adapter relink against hash-verified 7527fc44 baseline; overlay/command records in diagnostics/logs',
                      sleep_stage='stage 3 admission correction: administrator authorization separated from WindowServer identity; powered private-page test only',
                      ci_visual_status='user confirmed visible transparent-backdrop CI inversion on 01df8ecd',
                      renderer_baseline='ff42971e confirmed by user: Mesa / ATI FirePro V7900 / OpenGL 2.1 Mesa 26.2.4',
                      kernel_compiler_source='apple-oss-distributions/gcc@24a5ff4087d09b1170bc4653c85bf2d8361b2320',
                      reference_sha256=reference_hashes,
                      firmware_sha256={path.name:checksum(path) for path in firmware.iterdir()},
                      toolchain_patch_sha256={p.name:checksum(p) for p in (ROOT/'scripts/toolchain-patches').glob('*.patch')})
    (stage/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (stage/'BUILD.txt').write_text(
        'Experimental opt-in backing-completion comparison; system sleep stays blocked.\n'
        'Read RENDERING-TEST.txt. Retain 1e8579dd/7527fc44 and their recovery backups.\n'
        'QE/CI profile, clocks and sleep policy are unchanged; all four GL bundles are relinked.\n'
        'Kernel retained; GL adapters add opt-in backing alias bypass; pixel-store correction and 40% fan curve unchanged.\n'
        'Source commit: '+revision+'\n'
        'Built entirely on the Intel Mac; no agent G5 access or target execution of this build.\n'
        'Kernel/GA: PPC32. GL: four universal PPC32/PPC64 bundles.\n'
        'All '+str(validation['modules']['RadeonNI']['imports'])+' kernel imports match declared Apple 10.5.8 dependencies.\n'
        'PPC ABI1 compiler probe and 16 vtable comparisons pass.\n'
        'Userland system-import closure, exports, architecture and kld relocation checks pass.\n'
        'User confirmed QE and visible transparent-backdrop CI filtering on 01df8ecd.\n'
        'System sleep stays blocked. No PCI power change or GPU/VRAM restore is implemented.\n'
        'Read INSTALL.txt before any target action. Historical failed attempts are retained in the logs.\n'
        'Clone SOURCE.bundle on the build Mac with --branch '+branch+'.\n')
    for path in stage.rglob('*'):
        if path.is_symlink():
            raise ValueError('unexpected distribution symlink')
        executable = path.name in ('install.sh','uninstall.sh','manage.py','fan-monitor','sleep-rehearsal','maintenance-rehearsal','resource-rehearsal') or path.parent.name == 'diagnostics-tools' or '/Contents/MacOS/' in str(path)
        path.chmod(0o755 if path.is_dir() or executable else 0o644)
    manifest = {str(p.relative_to(stage)):checksum(p) for p in sorted(stage.rglob('*')) if p.is_file()}
    (stage/'MANIFEST.plist').write_bytes(plistlib.dumps(manifest))
    subprocess.run([sys.executable,'-E','-S',str(stage/'manage.py'),'verify'],check=True)
    output = ROOT/'build'/(name+'.zip')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(stage.rglob('*')):
            relative = str(Path(name)/path.relative_to(stage))
            if path.is_dir():
                continue
            entry = zipfile.ZipInfo(relative,date_time=archive_date)
            entry.create_system = 3
            entry.external_attr = (0o100000 | (path.stat().st_mode & 0o777)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry,path.read_bytes())
    with tempfile.TemporaryDirectory(prefix='radeonni-zip-verify-') as directory:
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC validation failed')
            archive.extractall(directory)
        subprocess.run([sys.executable,'-E','-S',str(Path(directory)/name/'manage.py'),'verify'],check=True)
    digest = checksum(output)
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n')
    result = dict(zip=str(output),sha256=digest,bytes=output.stat().st_size,
                  source_commit=revision,manifest_files=len(manifest),zip_crc_passed=True,
                  fresh_extraction_verified=True)
    (BUILD/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
