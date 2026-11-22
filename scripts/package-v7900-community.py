#!/usr/bin/env python3
"""Repackage known V7900 artifacts with accurate forum-facing notes.

This does not build new binaries or make a hardware qualification claim.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import tempfile
import zipfile
from leopard_macho import read

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/community-v7900/release'
SOURCES = {
    'Tiger': (ROOT/'build/tiger-v7900/complete-package/RadeonNI-Tiger-V7900-Experimental-7416253fd499.zip',
              'dc2fe1626287fb7856136e74d78f8c469d3dc336d3532d0b188fbc75a21a902a'),
    'Leopard': (ROOT/'build/RadeonNI-Leopard-V7900-20261109-7527fc44.zip',
                '3ba5e3e5351026d313742072ae88f22ab113893ce407333a230c7841f324e6a9'),
}
NOTES = {
    'Tiger': '''RADEONNI V7900 TIGER - EXPERIMENTAL COMMUNITY TEST

Target: Power Mac G5, Mac OS X 10.4.11 PowerPC, AMD FirePro V7900 PCI ID
1002:6704. Other cards and machines are not qualified by this package.
Read README.txt before installing. Install only from a known working recovery
setup; keep a backup and a recovery graphics card or volume available.

Includes automatic GPU fan control, hardware cursor, accelerated OpenGL,
Quartz Extreme and Core Image capability, and the scalar OpenGL trial used
successfully with Unreal and Unreal Tournament on one G5. This is not a
complete CFM/AltiVec safety proof; Unreal 1 had an audio-path exit crash.
Core Image filter correctness and sustained GPU/fan behavior are not fully
qualified. Do not use system sleep. The automatic fan policy is experimental.

The installer supports fresh installations and refuses an existing RadeonNI
stack; it does not upgrade or overwrite trial installs. Preserve all existing
backups. 256 MB in System Profiler refers to the accessible PCI aperture.
The forced 1080p experiment is excluded. A PC card may have no boot screen.
''',
    'Leopard': '''RADEONNI V7900 LEOPARD - EXPERIMENTAL COMMUNITY TEST

Target: Power Mac G5, Mac OS X 10.5.8 or Sorbet Leopard 10.5.9 PowerPC,
AMD FirePro V7900 PCI ID 1002:6704. Other cards are not qualified. Read
INSTALL.txt for verification, installation and exact backup/restore commands.
Keep a known working recovery volume and graphics card, and record the backup
path. This package does not flash firmware or change Open Firmware.

Includes the working V7900 framebuffer, hardware cursor, automatic GPU fan
control, 2D plugin and four universal PPC32/PPC64 GL bundles. Quartz Extreme
and Core Image were observed active on the user's G5; that does not prove all
rendering or filters are correct. Intermittent menu and text corruption was
observed on Leopard, even after later trials. Do not use system sleep.
The automatic fan policy is experimental, especially under sustained load.

UNREAL LIMITATION: The scalar CFM workaround that helped Unreal 1 and Unreal
Tournament on Tiger is NOT included in this Leopard baseline. Those games
have not been validated with this Leopard package. The failed forced 1080p
mode is excluded. A PC card may have no firmware boot screen. The older trial
descriptions and static reports are retained for provenance; this is being
shared as an experimental baseline, not a completed sleep or rendering fix.
''',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def archive_files(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip(): raise ValueError('CRC error: '+str(path))
        infos = z.infolist()
        if len({i.filename for i in infos}) != len(infos): raise ValueError('duplicate ZIP path')
        files = {}
        for item in infos:
            p = PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or item.is_dir() or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('unsafe ZIP member: '+item.filename)
            files[item.filename] = z.read(item)
        roots = {PurePosixPath(n).parts[0] for n in files}
        if len(roots) != 1: raise ValueError('expected one package root')
        root = roots.pop()+'/'
        return root, {n[len(root):]: d for n, d in files.items()}, {i.filename[len(root):]: i.external_attr for i in infos}

def verify_original(osname, files):
    if osname == 'Tiger':
        manifest = json.loads(files['manifest.json'])['files']
    else:
        manifest = plistlib.loads(files['MANIFEST.plist'])
    for name, expected in manifest.items():
        if name not in files or digest(files[name]) != expected:
            raise ValueError('manifest mismatch: '+osname+'/'+name)
    if set(files) != set(manifest) | ({'manifest.json'} if osname == 'Tiger' else {'MANIFEST.plist'}):
        raise ValueError('manifest inventory mismatch: '+osname)
    plist = plistlib.loads(files['payload/RadeonNI.kext/Contents/Info.plist'])
    profiles = list(plist['IOKitPersonalities'].values())
    if len(profiles) != 1 or profiles[0].get('IOPCIMatch') != '0x67041002' or not profiles[0].get('TemperatureFanControl'):
        raise ValueError('unexpected V7900/fan profile: '+osname)
    if not profiles[0].get('HWCursor') or not profiles[0].get('Accelerator'):
        raise ValueError('unexpected accelerator/cursor profile: '+osname)
    if osname == 'Leopard' and not profiles[0].get('BackingSurfaces'):
        raise ValueError('Leopard QE backing profile disabled')
    firmware = {'FW_PFP':'CAYMAN_pfp.bin', 'FW_ME':'CAYMAN_me.bin', 'FW_MC':'CAYMAN_mc.bin'}
    if osname == 'Leopard': firmware['FW_RLC']='CAYMAN_rlc.bin'
    for key, name in firmware.items():
        if profiles[0].get(key) != (ROOT/'firmware'/name).read_bytes():
            raise ValueError('embedded firmware mismatch: '+osname+'/'+key)
    with tempfile.TemporaryDirectory(prefix='radeonni-community-') as tmp:
        path = Path(tmp)/'binary'
        modules = ['RadeonNI.kext/Contents/MacOS/RadeonNI', 'RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA']
        modules += ['RadeonNIGLDriver'+s+'.bundle/Contents/MacOS/RadeonNIGLDriver'+s for s in ('','1','2','3')]
        for index, name in enumerate(modules):
            path.write_bytes(files['payload/'+name])
            arch = set(read(path))
            expected = {18, 0x1000012} if osname == 'Leopard' and index >= 2 else {18}
            if arch != expected: raise ValueError('wrong architecture '+name+': '+repr(arch))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for osname, (source, expected) in SOURCES.items():
        if digest(source.read_bytes()) != expected: raise ValueError('source ZIP hash mismatch: '+str(source))
        root, files, modes = archive_files(source)
        verify_original(osname, files)
        notes = NOTES[osname].encode('ascii')
        files['00-COMMUNITY-NOTES.txt'] = notes
        modes['00-COMMUNITY-NOTES.txt'] = 0o100644 << 16
        if osname == 'Tiger':
            manifest = json.loads(files['manifest.json']); manifest['files']['00-COMMUNITY-NOTES.txt'] = digest(notes)
            files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
        else:
            manifest = plistlib.loads(files['MANIFEST.plist']); manifest['00-COMMUNITY-NOTES.txt'] = digest(notes)
            files['MANIFEST.plist'] = plistlib.dumps(manifest)
        verify_original(osname, files)
        dest = OUT/('RadeonNI-'+osname+'-V7900-Community-Experimental.zip')
        with dest.open('xb') as output, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(root+name, (2020, 1, 1, 0, 0, 0))
                info.create_system = 3; info.external_attr = modes[name]; info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        _, check, _ = archive_files(dest); verify_original(osname, check)
        sha = digest(dest.read_bytes()); dest.with_suffix('.zip.sha256').write_text(sha+'  '+dest.name+'\n')
        print(osname, dest, sha, flush=True)

if __name__ == '__main__': main()
