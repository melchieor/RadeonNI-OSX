"""Ensure the compositor trial preserves the working V7900 fan profile."""
import copy
import importlib.util
from pathlib import Path
import plistlib
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
package=module('package',ROOT/'scripts/package-leopard-v7900.py')
profiles=module('profiles',ROOT/'scripts/configure-device-families.py')
class QeProfileTest(unittest.TestCase):
 def test_only_rehearsal_opt_in_delta_from_cursor_fan_profile(self):
  template=plistlib.loads((ROOT/'kext/RadeonNI/Info.plist').read_bytes())
  original=copy.deepcopy(template)
  previous=profiles.configure(template,['CAYMAN'],ROOT/'firmware')
  baseline=previous['IOKitPersonalities']['RadeonNI-CAYMAN']
  baseline['IOPCIMatch']='0x67041002';baseline['TemperatureFanControl']=True;baseline['BackingSurfaces']=True;baseline['HWCursor']=True
  result=package.qe_profile(template,ROOT/'firmware')
  self.assertEqual(set(result['IOKitPersonalities']),{'RadeonNI-V7900'})
  current=result['IOKitPersonalities']['RadeonNI-V7900']
  self.assertIs(current.pop('EnableSleepRehearsal'),True)
  baseline.pop('EnableSleepRehearsal',None)
  self.assertEqual(current,baseline)
  self.assertEqual(template,original)
  self.assertIs(current['SurfaceGate'],True)
  self.assertIs(current['Surfaces'],True)
  self.assertIs(current['Accelerator'],True)
  self.assertIs(current['TemperatureFanControl'],True)
  self.assertEqual(current['AccelCaps'],3)
if __name__=='__main__':unittest.main()
