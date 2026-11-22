#!/usr/bin/env python3
"""Build isolated scalar Leopard PPC32 CFM candidates on the Intel Mac."""
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
    parser.add_argument('bits', choices=('32',))
    parser.add_argument('--reconfigure', action='store_true')
    args = parser.parse_args()
    bits = args.bits
    source = ROOT / 'build/community-v7900/mesa-leopard-cfm'
    manifest = json.loads((source / 'radeonni-source-manifest.json').read_text())
    for name, expected in manifest['input_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Prepared Mesa inputs are stale: ' + name)
    tools = ROOT / 'third_party/leopard-toolchain/bin'
    cc = tools / 'powerpc-apple-darwin9-gcc'
    cpp = tools / 'powerpc-apple-darwin9-g++'
    if not cc.exists() or not cpp.exists():
        raise SystemExit('Finish the native cross-toolchain bootstrap first')
    sdk = ROOT / 'third_party/sdk-audit/extracted/MacOSX10.5.sdk'
    compat = ROOT / ('build/community-v7900/leopard-compat' + bits)
    compat.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'mesa/darwin8', compat / 'src', dirs_exist_ok=True)
    common = ['-m' + bits, '-mmacosx-version-min=10.5', '-mcpu=970',
              '-mlongcall', '-fno-strict-aliasing', '-isysroot', str(sdk)]
    if bits == '32':
        common.append('-mno-powerpc64')
    common.extend(['-mno-altivec', '-DRDN_CFM_NO_ALTIVEC=1'])
    for name in ('tiger_compat', 'tiger_emutls'):
        run([cc, *common, '-O2', '-c', compat/'src'/(name+'.c'),
             '-o', compat/(name+'.o')])
    run([tools/'ar', 'rcs', compat/'libtigercompat.a', compat/'tiger_compat.o'])
    atomic = subprocess.check_output([str(cc), '-m'+bits,
                                      '-print-file-name=libatomic.a'], text=True).strip()
    if not Path(atomic).is_file():
        raise SystemExit('Static target libatomic is missing: ' + atomic)
    cargs = common + ['-isystem', str(compat/'src/include')]
    cppargs = cargs + ['-include', str(compat/'src/tiger_compat.h')]
    links = ['-m'+bits, '-isysroot', str(sdk), '-mmacosx-version-min=10.5',
             '-nodefaultrpaths', '-static-libgcc', '-Wl,-dead_strip',
             str(compat/'libtigercompat.a'), atomic]
    cpplinks = links + ['-static-libstdc++', str(compat/'tiger_emutls.o')]
    scalar_runtime = ROOT/'build/community-v7900/libstdcxx-cfm/libstdc++.a'
    if not scalar_runtime.is_file():
        raise SystemExit('Prepare the isolated Leopard CFM runtime first')
    links.insert(0, '-B'+str(scalar_runtime.parent)+'/')
    cpplinks.insert(0, '-B'+str(scalar_runtime.parent)+'/')
    cross = ROOT / ('build/community-v7900/mesa-leopard-cfm'+bits+'.ini')
    cross.write_text(
        '[binaries]\n' + '\n'.join(name+' = '+repr(str(path)) for name, path in
          [('c', cc), ('cpp', cpp), ('objc', cc), ('ar', tools/'ar'),
           ('strip', tools/'strip'), ('ranlib', tools/'ranlib')]) +
        "\npkg-config = 'false'\n[properties]\nrdn_sdk = " + repr(str(sdk)) +
        '\n[built-in options]\nc_args = '+repr(cargs)+
        '\ncpp_args = '+repr(cppargs)+'\nobjc_args = '+repr(cargs)+
        '\nc_link_args = '+repr(links)+'\ncpp_link_args = '+repr(cpplinks)+
        "\n[host_machine]\nsystem = 'darwin'\ncpu_family = '"+
        ('ppc' if bits == '32' else 'ppc64')+
        "'\ncpu = 'ppc970'\nendian = 'big'\n")
    python = ROOT / 'third_party/build-python/bin/python'
    build = source / ('build-leopard-native'+bits)
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    env['PATH'] = str(ROOT/'third_party/host-tools/bin') + os.pathsep + str(python.parent) + os.pathsep + env['PATH']
    options = ['-Drdn=true', '-Dgallium-drivers=r600,softpipe', '-Dvulkan-drivers=',
               '-Dglx=disabled', '-Degl=disabled', '-Dgbm=disabled', '-Dllvm=disabled',
               '-Dplatforms=', '-Dgles1=disabled', '-Dgles2=disabled', '-Dzstd=disabled',
               '-Dvalgrind=disabled', '-Dlibunwind=disabled', '-Dvideo-codecs=',
               '-Dgallium-va=disabled', '-Dbuildtype=release', '-Doptimization=2',
               '-Dxmlconfig=disabled', '-Dshader-cache=enabled',
               '-Dshader-cache-max-size=64M', '-Db_ndebug=true']
    if args.reconfigure and (build/'build.ninja').exists():
        run([python, '-m', 'mesonbuild.mesonmain', 'setup', '--reconfigure',
             '--clearcache', build, source, '--cross-file', cross,
             '--wrap-mode=nodownload', *options], env=env)
    elif not (build/'build.ninja').exists():
        run([python, '-m', 'mesonbuild.mesonmain', 'setup', build, source,
             '--cross-file', cross, '--wrap-mode=nodownload', *options], env=env)
    targets = ['src/gallium/targets/rdn/RadeonNIGLDriver'+suffix+'.dylib'
               for suffix in ('', '1', '2', '3')]
    run(['ninja', '-j', os.environ.get('RDN_JOBS', '6'), '-C', build, *targets], env=env)


if __name__ == '__main__':
    main()
