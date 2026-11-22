#!/usr/bin/env python3
"""Audit the current source paths that expose video memory on Tiger.

A source audit cannot enumerate runtime aliases or establish that a mapping can
be blocked. Nonzero exit means a known source assumption has changed.
"""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
fb = (root / 'kext/RadeonNI/RadeonNI.cpp').read_text()
uc = (root / 'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
ga = (root / 'ga/RadeonNIGA.c').read_text()
mesa = (root / 'mesa/target/rdn_device_darwin.c').read_text()

def function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == '{') - (source[pos] == '}')
        if depth == 0:
            return source[brace:pos + 1]
    raise ValueError('Unclosed function: ' + signature)

def require(condition, description):
    if not condition:
        raise SystemExit('Source changed: ' + description)

aperture = function(fb, 'IOMemoryDescriptor *RadeonNI::apertureDescriptor()')
screen = function(fb, 'IODeviceMemory *RadeonNI::getApertureRange(')
vram = function(fb, 'IODeviceMemory *RadeonNI::getVRAMRange(')
client = function(uc, 'IOReturn RadeonNIUserClient::clientMemoryForType(')
mapper = function(uc, 'IOMemoryMap *RadeonNIUserClient::mapClientMemory(')
require('getDeviceMemoryWithRegister(FB_BAR)' in aperture, 'accelerator aperture')
require('IODeviceMemory::withSubRange' in screen and 'FB_BAR' in screen, 'framebuffer range')
require('getDeviceMemoryWithRegister(FB_BAR)' in vram, 'VRAM range')
require('RDN_UC_MEMORY_APERTURE' in client and 'apertureMemory()' in client, 'client aperture')
require('type!=RDN_UC_MEMORY_UNIQUE_PROBE' in mapper and 'super::mapClientMemory' in mapper,
        'unique redirect is limited to the test mapping')
for name, text in [('RadeonNIGA', ga), ('Mesa', mesa)]:
    require(re.search(r'IOConnectMapMemory\s*\([^;]*RDN_UC_MEMORY_APERTURE', text, re.S), name + ' aperture mapping')
require('mapDeviceMemoryWithRegister(FB_BAR)' in fb, 'kernel framebuffer map')
print(json.dumps({
 'source_assumptions_match': True,
 'mapping_paths': [
  {'owner':'driver kernel', 'path':'PCI framebuffer BAR kernel mapping', 'redirect_tested':False},
  {'owner':'accelerator clients', 'path':'IOConnectMapMemory of PCI framebuffer BAR', 'redirect_tested':False},
  {'owner':'IOFramebuffer', 'path':'system aperture subrange and VRAM range from PCI BAR', 'redirect_tested':False},
  {'owner':'private diagnostic client', 'path':'unique system-RAM mapping', 'redirect_tested':True}],
 'runtime_aliases_enumerated':False,
 'physical_bar_redirect_proven':False,
 'live_gart_and_gpu_access_excluded':False,
 'sleep_safe':False
}, indent=2, sort_keys=True))
