#!/usr/bin/env python3
"""Assemble an untested Leopard CFM candidate from verified local artifacts."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import tempfile
import zipfile
from leopard_macho import slices

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/community-v7900'
BASE=ROOT/'build/RadeonNI-Leopard-V7900-20261109-7527fc44.zip'
BASE_SHA='3ba5e3e5351026d313742072ae88f22ab113893ce407333a230c7841f324e6a9'
NAMES=['RadeonNIGLDriver'+s for s in ('','1','2','3')]

def load_script(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    tools=load_script('community',ROOT/'scripts/package-v7900-community.py')
    gld=load_script('gld_package',ROOT/'scripts/package-leopard-gld.py')
    if sha(BASE.read_bytes())!=BASE_SHA:raise ValueError('baseline ZIP hash mismatch')
    root,files,modes=tools.archive_files(BASE);tools.verify_original('Leopard',files)
    report=json.loads((OUT/'leopard-cfm32-validation.json').read_text())
    if report['errors'] or report['hardware_tested'] or report['unreal_tested']:
        raise ValueError('unexpected candidate audit state')
    ppc32=OUT/'mesa-leopard-cfm/build-leopard-native32/src/gallium/targets/rdn'
    with tempfile.TemporaryDirectory(prefix='radeonni-leopard-cfm-') as tmp:
        p64=Path(tmp)/'64';p64.mkdir()
        for name in NAMES:
            key='payload/'+name+'.bundle/Contents/MacOS/'+name
            base=slices(files[key]);candidate=ppc32/(name+'.dylib')
            if set(base)!={18,0x1000012} or sha(candidate.read_bytes())!=report['modules'][name]['sha256']:
                raise ValueError('candidate or baseline mismatch: '+name)
            (p64/(name+'.dylib')).write_bytes(base[0x1000012])
        universal=Path(tmp)/'universal';gld.package(ppc32,p64,universal)
        universal_manifest=json.loads((universal/'manifest.json').read_text())
        for name in NAMES:
            key='payload/'+name+'.bundle/Contents/MacOS/'+name
            old64=sha(slices(files[key])[0x1000012]);new=(universal/name).read_bytes()
            if sha(slices(new)[0x1000012])!=old64:raise ValueError('PPC64 baseline changed: '+name)
            files[key]=new
    note='''RADEONNI V7900 LEOPARD CFM CANDIDATE - UNTESTED ON HARDWARE

For Power Mac G5, Leopard 10.5.8/Sorbet 10.5.9, FirePro V7900 1002:6704.
This is an EXPERIMENTAL new build, not a stable release. Its kernel, 2D plugin,
profile, cursor and automatic fan are from the prior 7527fc44 baseline. Four
PPC32 GL slices were rebuilt for Leopard with the scalar approach that helped
Unreal 1 and Unreal Tournament on Tiger. Four PPC64 GL slices remain the
Leopard baseline. No Tiger driver binaries are included. The new Leopard GL
build has NOT been run on a G5 or tested with Unreal. Vector instructions
remain in two GCC runtime functions; complete CFM ABI safety is not proven.

QE/CI are enabled in the baseline profile; successful operation and filter
correctness with this candidate remain untested. Earlier Leopard builds showed
menu and text corruption. Automatic fan control is experimental. Do not use
system sleep. The failed forced 1080p mode is excluded. Keep an NVIDIA recovery
card or known working recovery volume and an independent backup. No firmware
flash or Open Firmware modification is performed.

FIRST read INSTALL.txt. Verify with /usr/bin/python -E -S manage.py verify,
then run sudo sh install.sh --check or --check-before-swap as appropriate.
After installing record the new backup path. If this candidate regresses,
use sudo sh uninstall.sh --restore with that exact backup path and reboot.
The original validation.json and SOURCE.bundle describe the BASELINE, not
these new GL slices. See LEOPARD-CFM-VALIDATION.json, CFM-PROVENANCE.json and
CFM-SOURCE-OVERLAYS.zip for the new candidate. Checksums are not signatures.
'''.encode('ascii')
    files['00-COMMUNITY-NOTES.txt']=note;modes['00-COMMUNITY-NOTES.txt']=0o100644<<16
    old=files['INSTALL.txt'].decode('utf-8');marker='Before installing (after reviewing the diagnostic output)'
    if marker not in old:raise ValueError('unexpected baseline instructions')
    files['INSTALL.txt']=note+b'\n'+old[old.index(marker):].encode('utf-8')
    files['BUILD.txt']=('Untested Leopard CFM GL candidate. Read 00-COMMUNITY-NOTES.txt.\n'
                        'Baseline validation and SOURCE.bundle apply only to retained baseline components.\n'
                        'PPC32 candidates use the Leopard SDK and 10.5 deployment target; PPC64 is baseline.\n'
                        'Actual V7900/Unreal/QE/CI/fan behavior has not been tested for this candidate.\n').encode()
    files['LEOPARD-CFM-VALIDATION.json']=(OUT/'leopard-cfm32-validation.json').read_bytes()
    files['CFM-UNIVERSAL-MANIFEST.json']=(json.dumps(universal_manifest,indent=2,sort_keys=True)+'\n').encode()
    source_manifest=json.loads((OUT/'mesa-leopard-cfm/radeonni-source-manifest.json').read_text())
    overlays=io.BytesIO()
    with zipfile.ZipFile(overlays,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,expected in sorted(source_manifest['input_sha256'].items()):
            path=ROOT/name;data=path.read_bytes()
            if sha(data)!=expected:raise ValueError('source changed after build: '+name)
            z.writestr(name,data)
        for name in ('scripts/prepare-mesa-leopard.sh','scripts/prepare-leopard-cfm-libstdcxx.py',
                     'scripts/build-mesa-leopard-cfm.py','scripts/validate-leopard-cfm-candidate.py'):
            z.writestr(name,(ROOT/name).read_bytes())
        z.writestr('radeonni-source-manifest.json',json.dumps(source_manifest,indent=2,sort_keys=True)+'\n')
    files['CFM-SOURCE-OVERLAYS.zip']=overlays.getvalue()
    provenance={'baseline_zip_sha256':BASE_SHA,'candidate_ppc32':report['modules'],
                'universal':universal_manifest,'source_commit':source_manifest['repository_commit'],
                'source_snapshot_sha256':sha(files['CFM-SOURCE-OVERLAYS.zip']),
                'runtime_manifest':json.loads((OUT/'libstdcxx-cfm/manifest.json').read_text()),
                'build_flags':['-mmacosx-version-min=10.5','-mno-altivec','-DRDN_CFM_NO_ALTIVEC=1'],
                'unreal_tested':False,'hardware_tested':False,'sleep_supported':False}
    files['CFM-PROVENANCE.json']=(json.dumps(provenance,indent=2,sort_keys=True)+'\n').encode()
    for name in ('prepare-leopard-cfm.log','prepare-leopard-runtime.log','build-leopard-cfm32.log','validate-leopard-cfm32.log'):
        files['build-logs/community-'+name]=(OUT/name).read_bytes()
    for name in files:
        if name not in modes:modes[name]=0o100644<<16
    files['MANIFEST.plist']=plistlib.dumps({n:sha(v) for n,v in sorted(files.items()) if n!='MANIFEST.plist'})
    tools.verify_original('Leopard',files)
    dest=OUT/'release/RadeonNI-Leopard-V7900-CFM-Community-Experimental.zip'
    with dest.open('xb') as output,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            item=zipfile.ZipInfo(root+name,(2020,1,1,0,0,0));item.create_system=3
            item.external_attr=modes[name];item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
    _,check,_=tools.archive_files(dest);tools.verify_original('Leopard',check)
    digest=sha(dest.read_bytes());dest.with_suffix('.zip.sha256').write_text(digest+'  '+dest.name+'\n')
    print(dest);print('sha256='+digest);print('UNTESTED ON HARDWARE: explicit controlled trial only')

if __name__=='__main__':main()
