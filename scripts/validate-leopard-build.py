#!/usr/bin/env python3
"""Static validation against declared Leopard KPIs and SDK dylib exports."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
from leopard_macho import read
from leopard_kext_abi import vtables, compare

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/leopard-v7900'
SDK = ROOT/'third_party/sdk-audit/extracted/MacOSX10.5.sdk'
REFERENCE = ROOT/'third_party/apple-leopard-update/reference'


def version(value):
    match = re.fullmatch(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:(d|a|b|fc)(\d+))?',value)
    if not match:
        raise ValueError('unrecognized bundle version: '+value)
    major,minor,patch,stage,build = match.groups()
    return (int(major),int(minor or 0),int(patch or 0),
            {None:4,'d':0,'a':1,'b':2,'fc':3}[stage],int(build or 0))


def validate():
    errors, modules = [], {}
    bundle = OUT/'kernel-final/RadeonNI.kext'
    info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    kernel = read(bundle/'Contents/MacOS/RadeonNI')
    if set(kernel) != {18} or kernel[18]['kind'] != 1:
        errors.append('kernel must be a PPC32 MH_OBJECT')
    imports = set(kernel[18]['imports'])
    real_kernel = set(read(REFERENCE/'mach_kernel')[18]['exports'])
    deps = {}
    locations = list((REFERENCE/'System/Library/Extensions/System.kext/PlugIns').glob('*.kext'))
    locations += [REFERENCE/'System/Library/Extensions'/(n+'.kext')
                  for n in ('IOGraphicsFamily', 'IOPCIFamily')]
    for path in locations:
        meta = plistlib.loads((path/'Info.plist').read_bytes())
        ident = meta['CFBundleIdentifier']
        if ident not in info['OSBundleLibraries']:
            continue
        binary = read(path/meta['CFBundleExecutable'])[18]
        requested = version(info['OSBundleLibraries'][ident])
        if not version(meta['OSBundleCompatibleVersion']) <= requested <= version(meta['CFBundleVersion']):
            errors.append('dependency version outside compatible range: '+ident)
        if meta.get('OSKernelResource'):
            allowed = set(binary['imports']) | set(binary['exports'])
            for name in imports & allowed:
                target = binary['aliases'].get(name, name)
                if target not in real_kernel:
                    errors.append('KPI symbol/alias absent from real kernel: '+name+' -> '+target)
        else:
            allowed = set(binary['exports'])
        deps[ident] = allowed
    unresolved = imports - set.union(*deps.values())
    if unresolved:
        errors.append('unresolved kernel imports: '+repr(sorted(unresolved)))
    if set(deps) != set(info['OSBundleLibraries']):
        errors.append('missing declared kernel dependency reference')
    env = dict(__import__('os').environ, RDN_OTOOL=str(ROOT/'third_party/leopard-toolchain/bin/otool'))
    check = subprocess.run(['bash',str(ROOT/'scripts/check-kext-relocs.sh'),str(bundle/'Contents/MacOS/RadeonNI')],
                           capture_output=True,text=True,env=env)
    if check.returncode:
        errors.append(check.stdout+check.stderr)
    modules['RadeonNI'] = dict(architecture='ppc32', imports=len(imports),
                               sha256=hashlib.sha256((bundle/'Contents/MacOS/RadeonNI').read_bytes()).hexdigest(),
                               unresolved=sorted(unresolved), relocation_check=check.stdout.strip(),
                               declared_dependencies=sorted(deps))

    # Symbol closure alone does not establish the PPC IOKit C++ ABI.
    # These comparisons reproduce the reserved-slot rule that rejected the
    # first build on Leopard, and require the old loader's zero terminator.
    own_vtables = vtables(bundle/'Contents/MacOS/RadeonNI')
    reference_vtables = {}
    for path in [REFERENCE/'mach_kernel'] + [
            REFERENCE/'System/Library/Extensions'/(n+'.kext')/n
            for n in ('IOGraphicsFamily','IOPCIFamily','IONDRVSupport')]:
        reference_vtables.update(vtables(path))
    class_pairs = [('RadeonNI','IOFramebuffer'), ('RadeonNIAccel','IOAccelerator'),
                   ('RadeonNIAGPShim','IOAGPDevice'), ('RadeonNIUserClient','IOUserClient'),
                   ('RadeonNISurfaceClient','IOUserClient'), ('RadeonNITelemetry','IOUserClient'),
                   ('RadeonNIVideoUserClient','IOUserClient'),
                   ('RadeonNIVideoMemory','IOGeneralMemoryDescriptor')]
    abi = {}
    for child_name, parent_name in class_pairs:
        child_symbol = '__ZTV%d%s' % (len(child_name),child_name)
        parent_symbol = '__ZTV%d%s' % (len(parent_name),parent_name)
        if child_symbol not in own_vtables or parent_symbol not in reference_vtables:
            errors.append('missing C++ ABI reference: '+child_name+' / '+parent_name)
            continue
        child, parent = own_vtables[child_symbol], reference_vtables[parent_symbol]
        failures = compare(child,parent)
        abi[child_name] = dict(superclass=parent_name, slots=len(child['entries']),
                              superclass_slots=len(parent['entries']),
                              terminated=child['terminated'], errors=failures)
        errors.extend(child_name+': '+failure for failure in failures)
    for child_name, _ in class_pairs:
        symbol = '__ZTVN%d%s9MetaClassE' % (len(child_name),child_name)
        if symbol not in own_vtables:
            errors.append('missing metaclass vtable: '+child_name)
            continue
        failures = compare(own_vtables[symbol],reference_vtables['__ZTV11OSMetaClass'])
        abi[child_name+'::MetaClass'] = dict(superclass='OSMetaClass', errors=failures,
            slots=len(own_vtables[symbol]['entries']), terminated=own_vtables[symbol]['terminated'])
        errors.extend(child_name+'::MetaClass: '+failure for failure in failures)
    import importlib.util
    probe_spec = importlib.util.spec_from_file_location('compiler_probe', ROOT/'scripts/check-leopard-kext-compiler.py')
    probe = importlib.util.module_from_spec(probe_spec)
    probe_spec.loader.exec_module(probe)
    rejected_abi = probe.check(ROOT/'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-g++',
                               report_name='gcc14-abi-rejection')
    if rejected_abi['passed']:
        errors.append('negative ABI regression unexpectedly passed for GCC 14')
    compiler_abi = probe.check()
    errors.extend(compiler_abi['errors'])
    modules['RadeonNI']['compiler_abi'] = compiler_abi
    modules['RadeonNI']['cpp_vtable_abi'] = abi

    library_cache = {}
    def library_exports(name, cpu, visiting=None):
        key = (name,cpu)
        if key in library_cache:
            return library_cache[key]
        if not name.startswith(('/usr/lib/', '/System/Library/Frameworks/', '/System/Library/PrivateFrameworks/')):
            raise ValueError('non-system dependency: '+name)
        visiting = set() if visiting is None else visiting
        if key in visiting:
            return set()
        visiting = visiting | {key}
        path = SDK/name.lstrip('/')
        # Prefer authenticated, updated libSystem from Apple's package.
        if name == '/usr/lib/libSystem.B.dylib':
            path = REFERENCE/'usr/lib/libSystem.B.dylib'
        meta = read(path)[cpu]
        result = set(meta['exports'])
        for dep in meta['dependencies']:
            result |= library_exports(dep,cpu,visiting)
        library_cache[key] = result
        return result

    allowed = {x.strip() for x in (ROOT/'gld/rdn_gld.exports').read_text().splitlines()
               if x.strip().startswith('_')}
    targets = [('RadeonNIGA',OUT/'ga-final/RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA',18),
               ('fan-monitor',OUT/'fan-monitor',18),('sleep-rehearsal',OUT/'sleep-rehearsal',18),('maintenance-rehearsal',OUT/'maintenance-rehearsal',18),('resource-rehearsal',OUT/'resource-rehearsal',18)]
    for probe_name in ('pixel-render-probe','pixel-render-probe-odd','pixel-render-probe-large','pixel-render-probe-atlas','sharetest','contexthandofftest','pbufferlifetest','pbufferpublishtest','pbufferthreadtest','backingsurfacetest','rendering-suite-visual','preferences-capture.dylib','capture-preflight'):
        pixel_probe = OUT/'pixel-probe'/probe_name
        if pixel_probe.is_file():
            targets.append((probe_name,pixel_probe,18))
    targets.extend((name,OUT/'qe-probes'/name,18) for name in ('qe-status','ci-filter-test','backing-test'))
    for bits,cpu in (('32',18),('64',0x1000012)):
        # Validate the exact universal deliverables, including both slices;
        # a relinked adapter must not accidentally validate older thin inputs.
        targets.extend(('RadeonNIGLDriver'+suffix+'-ppc'+bits,
                        OUT/'universal'/('RadeonNIGLDriver'+suffix),cpu)
                       for suffix in ('','1','2','3'))
    for name,path,cpu in targets:
        meta = read(path)[cpu]
        if meta['kind'] != (6 if name=='preferences-capture.dylib' else 2 if name.startswith('pixel-render-probe') or name in ('capture-preflight','sharetest','contexthandofftest','pbufferlifetest','pbufferpublishtest','pbufferthreadtest','backingsurfacetest','rendering-suite-visual','fan-monitor','sleep-rehearsal','maintenance-rehearsal','resource-rehearsal','pixel-render-probe','qe-status','ci-filter-test','backing-test') else 8) or meta['rpaths']:
            errors.append('unexpected file type or runtime search paths: '+name)
        if name.startswith('RadeonNIGLDriver') and set(meta['exports']) != allowed:
            errors.append('GLD export-list mismatch: '+name)
        if name == 'RadeonNIGA' and '_RadeonNIGAFactory' not in meta['exports']:
            errors.append('GA factory missing')
        provided = set()
        for dep in meta['dependencies']:
            provided |= library_exports(dep,cpu)
        missing = set(meta['imports']) - provided
        if missing:
            errors.append('unresolved userland imports in '+name+': '+repr(sorted(missing)))
        modules[name] = dict(cpu=cpu,subtype=meta['subtype'],kind=meta['kind'],
                             imports=len(meta['imports']),exports=len(meta['exports']),
                             dependencies=meta['dependencies'],rpaths=meta['rpaths'],
                             minimum_os_command=meta['minimum_os'],unresolved=sorted(missing),
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report = dict(passed=not errors,errors=errors,modules=modules,
                  kernel_reference='Apple-signed 10.5.8 Combo Update; declared KPI symbol sets and family binaries',
                  userland_reference='10.5 SDK dependency closure plus Apple-signed 10.5.8 libSystem',
                  runtime_tested=False,
                  note='PPC Leopard bundles normally omit LC_VERSION_MIN_MACOSX; deployment is set to 10.5 in the build flags.')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],errors=errors),indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(validate())
