#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import plistlib
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('accelerator_trial',ROOT/'scripts/build-tiger-accelerator-trial.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@unittest.skipUnless(module.firmware.DESTINATION.is_dir(),'staged firmware missing')
class AcceleratorProfile(unittest.TestCase):
    def setUp(self):
        p=ROOT/'build/tiger-v7900/profiles/v7900-framebuffer-only.plist'
        self.base=plistlib.loads(p.read_bytes())
        next(iter(self.base['IOKitPersonalities'].values()))['TemperatureFanControl']=True
        self.payloads={n:(module.firmware.DESTINATION/n).read_bytes() for n in module.firmware.INPUTS}

    def test_profile_has_verified_cayman_and_preserves_fan(self):
        result=plistlib.loads(module.create_profile(plistlib.dumps(self.base),self.payloads))
        entry=next(iter(result['IOKitPersonalities'].values()))
        self.assertTrue(entry['Accelerator']);self.assertTrue(entry['TemperatureFanControl'])
        self.assertFalse(entry['GAPlugin']);self.assertFalse(entry['Surfaces'])
        self.assertEqual(entry['IOPCIMatch'],'0x67041002')
        for kind in ('PFP','ME','MC'):
            self.assertEqual(entry['FW_'+kind],self.payloads['CAYMAN_'+kind.lower()+'.bin'])
        self.assertNotIn('AccelCaps',entry)

    def test_reject_corruption_wrong_device_and_no_fan(self):
        bad=dict(self.payloads);bad['CAYMAN_me.bin']=bad['TURKS_me.bin']
        with self.assertRaises(ValueError): module.create_profile(plistlib.dumps(self.base),bad)
        entry=next(iter(self.base['IOKitPersonalities'].values()));entry['IOPCIMatch']='0x675d1002'
        with self.assertRaises(ValueError): module.create_profile(plistlib.dumps(self.base),self.payloads)
        entry['IOPCIMatch']='0x67041002';entry['TemperatureFanControl']=False
        with self.assertRaises(ValueError): module.create_profile(plistlib.dumps(self.base),self.payloads)


if __name__=='__main__': unittest.main()
