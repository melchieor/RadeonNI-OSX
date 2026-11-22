#!/usr/bin/env python3
"""Create installer-identical Leopard ZIPs without bulky source history/logs."""
import hashlib
import importlib.util
from pathlib import Path
import plistlib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'build/community-v7900/release'
spec=importlib.util.spec_from_file_location('community',ROOT/'scripts/package-v7900-community.py')
community=importlib.util.module_from_spec(spec);spec.loader.exec_module(community)

def main():
    for suffix in ('','-CFM'):
        source=RELEASE/('RadeonNI-Leopard-V7900'+suffix+'-Community-Experimental.zip')
        root,files,modes=community.archive_files(source);community.verify_original('Leopard',files)
        dropped=[n for n in files if n=='SOURCE.bundle' or n.startswith('build-logs/') or n=='diagnostics/git-tree.json']
        for name in dropped:del files[name];del modes[name]
        note=('SLIM TRANSPORT: The driver payload, firmware, licenses, installers,\n'
              'recovery instructions and validation reports are retained unchanged.\n'
              'The baseline SOURCE.bundle, build logs and SDK git-tree inventory\n'
              'are omitted to reduce download size. Obtain the corresponding full\n'
              'community ZIP for those materials and full reproduction. The exact\n'
              'same experimental and hardware warnings apply.\n\n').encode('ascii')
        for name in ('00-COMMUNITY-NOTES.txt','INSTALL.txt','BUILD.txt'):
            files[name]=note+files[name]
        files['MANIFEST.plist']=plistlib.dumps({n:community.digest(v) for n,v in sorted(files.items()) if n!='MANIFEST.plist'})
        community.verify_original('Leopard',files)
        dest=RELEASE/('RadeonNI-Leopard-V7900'+suffix+'-Community-Slim.zip')
        with dest.open('xb') as stream,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(files.items()):
                item=zipfile.ZipInfo(root+name,(2020,1,1,0,0,0));item.create_system=3
                item.external_attr=modes[name];item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
        _,result,_=community.archive_files(dest);community.verify_original('Leopard',result)
        digest=hashlib.sha256(dest.read_bytes()).hexdigest()
        dest.with_suffix('.zip.sha256').write_text(digest+'  '+dest.name+'\n')
        print(dest.name,'omitted',len(dropped),'files; sha256',digest,flush=True)

if __name__=='__main__':main()
