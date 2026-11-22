#!/usr/bin/env python3
"""Experimentally build all four Tiger GL modules on the Intel Mac, using the pinned SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    print('+ ' + repr([str(x) for x in command]), flush=True)
    subprocess.run([str(x) for x in command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bits', choices=('32', '64'))
    parser.add_argument('--reconfigure', action='store_true')
    parser.add_argument('--scalar-cfm', action='store_true',
                        help='isolated experiment: disable AltiVec for legacy CFM stack alignment')
    args = parser.parse_args()
    bits = args.bits
    if args.scalar_cfm and bits != '32':
        parser.error('CFM stack-alignment experiment is PPC32 only')
    source = ROOT / ('build/tiger-v7900/mesa-cfm-scalar' if args.scalar_cfm else 'build/tiger-v7900/mesa-26.2.4')
    manifest = json.loads((source / 'radeonni-source-manifest.json').read_text())
    for name, expected in manifest['input_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Prepared Mesa inputs are stale: ' + name)
    tools = ROOT / 'third_party/leopard-toolchain/bin'
    cc = tools / 'powerpc-apple-darwin9-gcc'
    cpp = tools / 'powerpc-apple-darwin9-g++'
    if not cc.exists() or not cpp.exists():
        raise SystemExit('Finish the native cross-toolchain bootstrap first')
    sdk = ROOT / 'build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk'
    compat = ROOT / ('build/tiger-v7900/compat' + bits + ('-cfm-scalar' if args.scalar_cfm else ''))
    compat.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'mesa/darwin8', compat / 'src', dirs_exist_ok=True)
    common = ['-m' + bits, '-mmacosx-version-min=10.4', '-mcpu=970',
              '-mlongcall', '-fno-strict-aliasing', '-isysroot', str(sdk)]
    if bits == '32':
        common.append('-mno-powerpc64')
    if args.scalar_cfm:
        common.extend(['-mno-altivec','-DRDN_CFM_NO_ALTIVEC=1'])
    for name in ('tiger_compat', 'tiger_emutls', 'tiger_unix2003'):
        run([cc, *common, '-O2', '-c', compat/'src'/(name+'.c'),
             '-o', compat/(name+'.o')])
    run([tools/'ar', 'rcs', compat/'libtigercompat.a', compat/'tiger_compat.o'])
    gpsave = compat / 'gpsave.o'
    run([cc, *common, '-c', ROOT/'third_party/gcc-14-darwin/libgcc/config/rs6000/darwin-gpsave.S', '-o', gpsave])
    atomic = subprocess.check_output([str(cc), '-m'+bits,
                                      '-print-file-name=libatomic.a'], text=True).strip()
    if not Path(atomic).is_file():
        raise SystemExit('Static target libatomic is missing: ' + atomic)
    # Configure executables are never run. Tiger's SDK crt1.o is rejected by
    # this ld64; a trap-only helper permits link checks. Never add it to bundles.
    probe_stub = compat/'configure-only-dyld-trap.o'
    asm = compat/'configure-only-dyld-trap.s'
    asm.write_text('.text\n.globl dyld_stub_binding_helper\ndyld_stub_binding_helper:\n.long 0x7fe00008\n')
    run([cc, *common, '-c', asm, '-o', probe_stub])
    wrappers = []
    for name, compiler in [('cc',cc),('cxx',cpp)]:
        wrapper=compat/('meson-'+name)
        wrapper.write_text("#!/bin/sh\nprobe=1\nfor arg do case \"$arg\" in -c|-E|-S|-bundle|-dynamiclib|-shared|-Wl,-bundle|-Wl,-dylib) probe=0;; esac; done\nif [ \"$probe\" = 1 ]; then exec \""+str(compiler)+"\" \"$@\" -nostartfiles -Wl,-e,_main \""+str(probe_stub)+"\"; fi\nexec \""+str(compiler)+"\" \"$@\"\n")
        wrapper.chmod(0o755);wrappers.append(wrapper)
    cargs = common + ['-isystem', str(compat/'src/include')]
    cppargs = cargs + ['-include', str(compat/'src/tiger_compat.h')]
    links = ['-m'+bits, '-isysroot', str(sdk), '-mmacosx-version-min=10.4',
             '-nodefaultrpaths', '-static-libgcc', '-Wl,-dead_strip',
             str(compat/'libtigercompat.a'), atomic, str(gpsave), str(compat/'tiger_unix2003.o')]
    if args.scalar_cfm:
        scalar_runtime = ROOT/'build/tiger-v7900/libstdcxx-cfm/libstdc++.a'
        if not scalar_runtime.is_file():
            raise SystemExit('Prepare the isolated CFM libstdc++ archive before linking')
        # Darwin GCC resolves -static-libstdc++ to an absolute archive and
        # bypasses -L. -B changes the driver's archive lookup without forcing
        # every archive member (and its initializers) into the module.
        links.insert(0, '-B'+str(scalar_runtime.parent)+'/')
    cpplinks = links + ['-static-libstdc++', str(compat/'tiger_emutls.o')]
    cross = ROOT / ('build/tiger-v7900/mesa-tiger-native'+bits+('-cfm-scalar' if args.scalar_cfm else '')+'.ini')
    cross.write_text(
        '[binaries]\n' + '\n'.join(name+' = '+repr(str(path)) for name, path in
          [('c', wrappers[0]), ('cpp', wrappers[1]), ('objc', wrappers[0]), ('ar', tools/'ar'),
           ('strip', tools/'strip'), ('ranlib', tools/'ranlib')]) +
        "\npkg-config = 'false'\n[properties]\nrdn_sdk = " + repr(str(sdk)) +
        '\n[built-in options]\nc_args = '+repr(cargs)+
        '\ncpp_args = '+repr(cppargs)+'\nobjc_args = '+repr(cargs)+
        '\nc_link_args = '+repr(links)+'\ncpp_link_args = '+repr(cpplinks)+
        "\n[host_machine]\nsystem = 'darwin'\ncpu_family = '"+
        ('ppc' if bits == '32' else 'ppc64')+
        "'\ncpu = 'ppc970'\nendian = 'big'\n")
    python = ROOT / 'third_party/build-python/bin/python'
    build = source / ('build-tiger-native'+bits)
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    env['PATH'] = str(ROOT/'third_party/host-tools/bin') + os.pathsep + str(python.parent) + os.pathsep + env['PATH']
    options = ['-Drdn=true', '-Dgallium-drivers=r600,softpipe', '-Dvulkan-drivers=',
               '-Dglx=disabled', '-Degl=disabled', '-Dgbm=disabled', '-Dllvm=disabled',
               '-Dplatforms=', '-Dgles1=disabled', '-Dgles2=disabled', '-Dzstd=disabled',
               '-Dvalgrind=disabled', '-Dlibunwind=disabled', '-Dvideo-codecs=',
               '-Dgallium-va=disabled', '-Dbuildtype=release', '-Doptimization=2',
               '-Dxmlconfig=disabled', '-Dshader-cache=disabled',
               '-Dshader-cache-max-size=64M', '-Db_ndebug=true']
    if args.reconfigure and (build/'build.ninja').exists():
        run([python, '-m', 'mesonbuild.mesonmain', 'setup', '--reconfigure',
             '--clearcache', build, source, '--cross-file', cross,
             '--wrap-mode=nodownload', *options], env=env)
    elif not (build/'build.ninja').exists():
        run([python, '-m', 'mesonbuild.mesonmain', 'setup', build, source,
             '--cross-file', cross, '--wrap-mode=nodownload', *options], env=env)
    run([python, '-m', 'mesonbuild.mesonmain', 'configure', build,
         '-Dc_link_args='+repr(links), '-Dcpp_link_args='+repr(cpplinks)], env=env)
    targets = ['src/gallium/targets/rdn/RadeonNIGLDriver'+suffix+'.dylib'
               for suffix in ('', '1', '2', '3')]
    if args.scalar_cfm and args.reconfigure:
        # The driver resolves libstdc++ through -B; Ninja cannot infer this
        # hidden archive dependency. Force relinking after runtime changes.
        for suffix in ('', '1', '2', '3'):
            marker=build/('src/gallium/targets/rdn/RadeonNIGLDriver'+suffix+
                          '.dylib.p/gld_RadeonNIGLDriver.c.o')
            if marker.exists(): marker.touch()
    run(['ninja', '-j', os.environ.get('RDN_JOBS', '6'), '-C', build, *targets], env=env)


if __name__ == '__main__':
    main()
