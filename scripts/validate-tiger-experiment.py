#!/usr/bin/env python3
"""Audit experimental Tiger artifacts; this never marks them installable."""
import argparse,collections,hashlib,json,plistlib,struct
from pathlib import Path
from leopard_macho import read
from leopard_kext_abi import vtables,compare,object_data,symbol_bytes
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900';SDK=OUT/'sdk-audit/extracted/MacOSX10.4u.sdk';REF=OUT/'apple-reference'

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--fan-experiment',action='store_true',help='audit the separate, opt-in V7900 fan build')
 parser.add_argument('--cinema-experiment',action='store_true',help='audit the separate fan-enabled Cinema mode build')
 parser.add_argument('--kernel-path',type=Path,help='audit an explicit experimental kernel')
 parser.add_argument('--report-path',type=Path,help='write an explicit report for an experimental kernel')
 args=parser.parse_args()
 if bool(args.kernel_path)!=bool(args.report_path):parser.error('--kernel-path and --report-path must be supplied together')
 if args.cinema_experiment and not args.fan_experiment:parser.error('--cinema-experiment requires --fan-experiment')
 cache={}
 def dependencies(names):
  seen=set();exports=set();errors=[];todo=list(names)
  while todo:
   name=todo.pop()
   if name in seen:continue
   seen.add(name)
   if not name.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')):
    errors.append('non-system dependency '+name);continue
   try:
    if name not in cache:
     path=REF/'usr/lib/libSystem.B.dylib' if name=='/usr/lib/libSystem.B.dylib' else SDK/name.lstrip('/')
     cache[name]=read(path)[18]
    data=cache[name];exports.update(data['exports']);todo.extend(data['dependencies'])
   except (OSError,KeyError,ValueError) as e:errors.append(name+': '+str(e))
  return exports,errors
 root=OUT/'mesa-26.2.4/build-tiger-native32/src/gallium/targets/rdn'
 files={'RadeonNIGA':OUT/'ga-experiment/RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA'}
 files.update({'RadeonNIGLDriver'+x:root/('RadeonNIGLDriver'+x+'.dylib') for x in ('','1','2','3')})
 modules={}
 for name,path in files.items():
  data=read(path)[18];exports,errors=dependencies(data['dependencies'])
  helper_check=None
  if name.startswith('RadeonNIGLDriver'):
   try:
    helper_check=(symbol_bytes(path,'dyld_stub_binding_helper',16)==symbol_bytes(SDK/'usr/lib/bundle1.o','dyld_stub_binding_helper',16))
   except (OSError,ValueError,StopIteration,IndexError):helper_check=False
  modules[name]={'sdk_bundle_helper_prefix_matches':helper_check,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'kind':data['kind'],
   'dependencies':data['dependencies'],'rpaths':data['rpaths'],
   'unresolved':sorted(set(data['imports'])-exports),'dependency_errors':errors}
 kernel=args.kernel_path if args.kernel_path else OUT/('kernel-cinema-experiment' if args.cinema_experiment else 'kernel-fan-experiment' if args.fan_experiment else 'kernel-experiment')/'RadeonNI.kext/Contents/MacOS/RadeonNI'
 references=[REF/'mach_kernel']+[REF/'System/Library/Extensions'/(n+'.kext')/n for n in ('IOGraphicsFamily','IOPCIFamily','IONDRVSupport')]
 own=vtables(kernel);parents={};kernel_exports=set();unresolved_parent_slots={}
 for f in references:
  tables=vtables(f);meta=read(f)[18]
  if meta['kind'] != 1:
   data,sections,symbols=object_data(f);addresses=collections.defaultdict(list)
   for name,typ,section,value in symbols:
    if not typ & 0xe0 and typ & 0x0e == 0x0e:addresses[value].append(name)
   for name,table in tables.items():
    raw=symbol_bytes(f,name,8+4*len(table['entries']));missing_slots=0
    for i,(old,local) in enumerate(table['entries']):
     if old!='<unrelocated>':continue
     addr=struct.unpack_from('>I',raw,8+4*i)[0];names=addresses.get(addr,[])
     if not names:missing_slots+=1;continue
     reserved=[n for n in names if '_RESERVED' in n]
     table['entries'][i]=(reserved[0] if reserved else names[0],True)
    if missing_slots:unresolved_parent_slots[name]=missing_slots
  parents.update(tables);kernel_exports.update(meta['exports'])
 pairs=[('RadeonNI','IOFramebuffer'),('RadeonNIAccel','IOAccelerator'),('RadeonNIAGPShim','IOAGPDevice'),('RadeonNIUserClient','IOUserClient'),('RadeonNISurfaceClient','IOUserClient'),('RadeonNITelemetry','IOUserClient'),('RadeonNIVideoUserClient','IOUserClient')]
 abi={}
 for c,p in pairs:
  a='__ZTV%d%s'%(len(c),c);b='__ZTV%d%s'%(len(p),p)
  abi[c]=compare(own[a],parents[b]) if a in own and b in parents else ['missing reference']
  if b in unresolved_parent_slots:abi[c].append('unresolved parent slots: '+str(unresolved_parent_slots[b]))
  meta='__ZTVN%d%s9MetaClassE'%(len(c),c)
  abi[c+'::MetaClass']=compare(own[meta],parents['__ZTV11OSMetaClass']) if meta in own and '__ZTV11OSMetaClass' in parents else ['missing metaclass']
  if '__ZTV11OSMetaClass' in unresolved_parent_slots:abi[c+'::MetaClass'].append('unresolved parent metaclass slots')
 compat=read(REF/'System/Library/Extensions/System.kext/PlugIns/System6.0.kext/kernel.6.0')[18]
 plugins=REF/'System/Library/Extensions/System.kext/PlugIns'
 shared={}
 for name in ('IOKit6.0','Libkern6.0','Mach6.0'):
  with (plugins/(name+'.kext')/'Info.plist').open('rb') as f:info=plistlib.load(f)
  shared[info['CFBundleIdentifier']]={key:info.get(key) for key in ('CFBundleVersion','OSBundleCompatibleVersion','OSBundleSharedExecutableIdentifier')}
 with (ROOT/'kext/RadeonNI/Info.plist').open('rb') as f:declared=plistlib.load(f)['OSBundleLibraries']
 compat_names=set(compat['imports'])|set(compat['exports']);original_kernel=set(read(REF/'mach_kernel')[18]['exports'])
 alias_errors=[]
 for name in set(read(kernel)[18]['imports']) & compat_names:
  if compat['aliases'].get(name,name) not in original_kernel:alias_errors.append(name+' -> '+compat['aliases'].get(name,name))
 missing=sorted(set(read(kernel)[18]['imports'])-kernel_exports-compat_names)
 # Each module necessarily defines _kmod_info. Other exported names that
 # collide with a declared/reference kernel or compatibility export may be
 # rejected by Tiger kld even when all imports and ABI checks pass.
 collisions=sorted((set(read(kernel)[18]['exports']) & (kernel_exports | compat_names)) - {'_kmod_info'})
 thunk_expect=[('__ZTV12IOUserClient',16,'__ZN8OSObject4initEv'),
               ('__ZTV12IOUserClient',82,'__ZN15IORegistryEntry4initEP12OSDictionary'),
               ('__ZTV11IOPCIDevice',105,'__ZN15IORegistryEntry13setPropertiesEP8OSObject')]
 thunk_evidence={}
 for table,slot,target in thunk_expect:
  actual=parents.get(table,{}).get('entries',[])
  thunk_evidence[table+':'+str(slot)]={'expected':target,'observed':actual[slot][0] if len(actual)>slot else None}
 report={'installable':False,'reason':'Experimental C++ compatibility forwarding and kernel dependency resolution remain unvalidated; no Tiger runtime or V7900 test.',
  'sdk_mirror_consistency_only':True,
  'unresolved_release_gates':['Legacy Tiger installer selects Turks firmware, not Cayman',
   ('V7900 automatic fan policy is compiled experimentally but is not enabled in a profile or validated on Tiger' if args.fan_experiment else 'V7900 automatic temperature fan policy is disabled in this Tiger build'),
   'Tiger libc compatibility semantics and Tiger/V7900 runtime remain untested',
   'No qualified Tiger-specific V7900 installer or recovery package'],
  'modules':modules,'kernel':{'sha256':hashlib.sha256(kernel.read_bytes()).hexdigest(),
  'declared_kernel_dependencies':declared,'tiger_pseudoextension_shared_executables':shared,
  'abi_comparisons':abi,'thunk_target_vtable_evidence':thunk_evidence,'unresolved_against_reference_union':missing,'compatibility_alias_errors':alias_errors,'export_collisions':collisions,
  'warning':'Union plus kernel.6.0 alias check is not a full declared-dependency/version or runtime loader test.'}}
 destination=args.report_path if args.report_path else OUT/('experimental-validation-cinema.json' if args.cinema_experiment else 'experimental-validation-fan.json' if args.fan_experiment else 'experimental-validation.json')
 if args.report_path and destination.exists():raise SystemExit('Refusing to overwrite explicit report')
 destination.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
