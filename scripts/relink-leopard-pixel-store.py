#!/usr/bin/env python3
"""Relink only the GL adapter against verified delivered Mesa objects on Intel Mac.
No shared Mesa source, object, binary or SDK is modified. Run with 32 or 64.
"""
import argparse,hashlib,json,shlex,subprocess,zipfile,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/leopard-v7900/pixel-store-relink'
BASE='RadeonNI-Leopard-V7900-20261109-7527fc44.zip'
BASE_SHA='3ba5e3e5351026d313742072ae88f22ab113893ce407333a230c7841f324e6a9'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,cwd):
 print('+ '+shlex.join([str(x) for x in args]),flush=True)
 subprocess.run([str(x) for x in args],cwd=cwd,check=True)
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('bits',choices=['32','64']);parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();bits=args.bits
 base=ROOT/'build'/BASE
 assert sha(base)==BASE_SHA,'Base delivered ZIP hash mismatch'
 spec=importlib.util.spec_from_file_location('gld_package',ROOT/'scripts/package-leopard-gld.py');pkg=importlib.util.module_from_spec(spec);spec.loader.exec_module(pkg)
 source=ROOT/'third_party/mesa-26.2.4';build=source/('build-leopard-native'+bits)
 assert '#define MAX_CLIENT_ATTRIB_STACK_DEPTH 16' in (source/'src/mesa/main/config.h').read_text()
 output=args.output.resolve()/('ppc'+bits);output.mkdir(parents=True,exist_ok=True)
 sdk=ROOT/'third_party/sdk-audit/extracted/MacOSX10.5.sdk'
 generated=output/'rdn_dispatch_gen.c'
 run(['python3',ROOT/'gld/gen_dispatch.py',sdk/'System/Library/Frameworks/OpenGL.framework/Headers/gliDispatch.h',generated],ROOT)
 provenance={'base_zip_sha256':BASE_SHA,'bits':bits,'base_manifest_sha256':sha(source/'radeonni-source-manifest.json'),
  'overlay_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'gld/gen_dispatch.py',ROOT/'gld/rdn_mesa.c',ROOT/'gld/rdn_glue.h']},'modules':{}}
 with zipfile.ZipFile(base) as archive:
  for suffix in ['','1','2','3']:
   name='RadeonNIGLDriver'+suffix;target='src/gallium/targets/rdn/'+name+'.dylib'
   delivered=archive.read(next(n for n in archive.namelist() if n.endswith('/'+name+'.bundle/Contents/MacOS/'+name)))
   cpu=18 if bits=='32' else 0x1000012
   assert pkg.universal(delivered)[cpu]==sha(build/target),'Base thin module differs from delivered slice'
   lines=subprocess.check_output(['ninja','-t','commands',target],cwd=build,text=True).splitlines()
   replacements={};commands=[]
   for object_name,input_source in [('meson-generated_.._rdn_dispatch_gen.c.o',generated),('gld_rdn_mesa.c.o',ROOT/'gld/rdn_mesa.c')]:
    matches=[line for line in lines if ' -c ' in line and '/'+object_name in line]
    assert len(matches)==1,(name,object_name,len(matches))
    parts=shlex.split(matches[0]);original=parts[parts.index('-o')+1];new=output/(name+'-'+object_name)
    result=[parts[0],'-I'+str(ROOT/'gld')];i=1
    while i<len(parts):
     item=parts[i]
     if item in ['-MF','-MQ']:i+=2;continue
     if item=='-MD':i+=1;continue
     if item=='-o':result+=['-o',str(new)];i+=2;continue
     if item=='-c':result+=['-c',str(input_source)];i+=2;continue
     result.append(item);i+=1
    assert '-mmacosx-version-min=10.5' in result
    run(result,build);commands.append(result);replacements[original]=str(new)
   link=shlex.split(lines[-1]);assert link[link.index('-o')+1]==target
   result=[];i=0
   while i<len(link):
    if link[i]=='-o':result+=['-o',str(output/(name+'.dylib'))];i+=2;continue
    result.append(replacements.get(link[i],link[i]));i+=1
   assert '-nodefaultrpaths' in result and '-mmacosx-version-min=10.5' in result
   run(result,build)
   provenance['modules'][name]={'base_thin_sha256':sha(build/target),'output_sha256':sha(output/(name+'.dylib')),'compile_commands':commands,'link_command':result}
 (output/'relink-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 print('Finished isolated PPC'+bits+' adapter relink',flush=True)
if __name__=='__main__':main()
