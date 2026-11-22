#!/usr/bin/env python3
"""Build tiny non-device Tiger kexts to compare kernel symbol visibility."""
import hashlib,json,plistlib,subprocess,zipfile
from pathlib import Path
from leopard_macho import read
root=Path(__file__).resolve().parents[1]
out=root/'build/tiger-v7900/symbol-link-check-v3-20261118'
out.mkdir(parents=True,exist_ok=True)
sdk=root/'build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk'
cc=root/'third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-gcc'
flags=['-m32','-Os','-mkernel','-fno-pic','-fno-PIE','-static','-fno-common','-isysroot',str(sdk),'-mmacosx-version-min=10.4','-DKERNEL','-DKERNEL_PRIVATE','-nostdinc','-I'+str(sdk/'System/Library/Frameworks/Kernel.framework/Headers')]
files={}
for short,ident,symbols in [('Raw','org.osxgpu.linkcheck.Raw',['kvtophys64']),('Pmap','org.osxgpu.linkcheck.Pmap',['pmap_find_phys','kernel_pmap'])]:
 b=out/(short+'.kext')/'Contents';(b/'MacOS').mkdir(parents=True,exist_ok=True)
 declarations='\n'.join('extern char %s;' % n for n in symbols)
 uses='\n'.join('  slot%d = (unsigned long)&%s;' % (i,n) for i,n in enumerate(symbols))
 src='''#include <mach/mach_types.h>\n%s\nstatic volatile unsigned long slot0,slot1;\nstatic kern_return_t begin(kmod_info_t *i,void *d) { (void)i;(void)d;\n%s\n return KERN_SUCCESS; }\nstatic kern_return_t end(kmod_info_t *i,void *d) {(void)i;(void)d;return KERN_SUCCESS;}\nKMOD_EXPLICIT_DECL(%s,"0.1.0",begin,end)\n'''%(declarations,uses,ident)
 source=out/(short+'.c');source.write_text(src)
 obj=out/(short+'.o');binary=b/'MacOS'/short
 subprocess.run([str(cc),*flags,'-c',str(source),'-o',str(obj)],check=True)
 subprocess.run([str(cc),'-m32','-isysroot',str(sdk),'-mmacosx-version-min=10.4','-static','-nostdlib','-r',str(obj),'-Wl,-new_linker','-o',str(binary)],check=True)
 meta=read(binary)[18];imports=set(meta['imports']);expected={'_'+n for n in symbols}
 if meta['kind']!=1 or imports!=expected:raise SystemExit('Unexpected imports for %s: %r'%(short,imports))
 info={'CFBundleIdentifier':ident,'CFBundleExecutable':short,'CFBundleName':short,'CFBundleVersion':'0.1.0','CFBundlePackageType':'KEXT','OSBundleLibraries':{'com.apple.kernel.iokit':'6.0','com.apple.kernel.libkern':'6.0','com.apple.kernel.mach':'6.0','com.apple.iokit.IOGraphicsFamily':'1.0','com.apple.iokit.IOPCIFamily':'1.0'}}
 (b/'Info.plist').write_bytes(plistlib.dumps(info))
 for path in (b/'Info.plist',binary):files[str(path.relative_to(out))]=path.read_bytes()
files['README.txt']=b'''EXPERIMENTAL TIGER LOADER TEST; NO DEVICE PERSONALITIES.\nLoads small independent kexts referencing symbol addresses without calling\nthem. No Radeon kext replacement, hardware access or sleep. A loader defect or\nkernel incompatibility could still panic. Do not install in Extensions.\n'''
files['run-offline.sh']=b'''#!/bin/sh
set -u
cd "$(dirname "$0")" || exit 1
for name in Raw Pmap; do
  dir=$(mktemp -d /tmp/rdn-symbol-check.XXXXXXXX) || exit 1
  echo "=== $name: non-loading linker diagnostics ==="
  /sbin/kextload -z -c -t -n -v 3 -s "$dir" "./$name.kext" 2>&1
  code=$?
  echo "LINK_CHECK_EXIT=$code"
  /bin/ls -l "$dir"
  /bin/rm -rf "$dir"
done
'''
files['run-load.sh']=(root/'g5/tiger-symbol-link-check.sh').read_bytes()
files['manifest.json']=(json.dumps({'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}},indent=2,sort_keys=True)+'\n').encode()
dest=out/'RadeonNI-Tiger-Symbol-Link-Check.zip'
with dest.open('xb') as f:
 with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
  for n,d in files.items():
   e=zipfile.ZipInfo('RadeonNI-Tiger-Symbol-Link-Check/'+n,(2020,1,1,0,0,0));e.create_system=3;e.external_attr=(0o100755 if '/MacOS/' in n or n.endswith('.sh') else 0o100644)<<16;e.compress_type=zipfile.ZIP_DEFLATED;z.writestr(e,d)
print(dest,'sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())
