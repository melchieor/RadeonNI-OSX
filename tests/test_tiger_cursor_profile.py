#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import plistlib
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cursor_trial',ROOT/'scripts/build-tiger-cursor-trial.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CursorProfile(unittest.TestCase):
    def setUp(self):
        self.info={'IOKitPersonalities':{'RadeonNI':{'IOPCIMatch':'0x67041002','Accelerator':True,
                   'GAPlugin':True,'TemperatureFanControl':True,'HWCursor':False}}}

    def test_only_cursor_changes(self):
        result=plistlib.loads(module.cursor_profile(plistlib.dumps(self.info)))
        entry=result['IOKitPersonalities']['RadeonNI'];self.assertIs(entry['HWCursor'],True)
        entry['HWCursor']=False;self.assertEqual(result,self.info)

    def test_wrong_board_or_disabled_fan_rejected(self):
        entry=self.info['IOKitPersonalities']['RadeonNI']
        entry['IOPCIMatch']='0x675d1002'
        with self.assertRaises(ValueError):module.cursor_profile(plistlib.dumps(self.info))
        entry['IOPCIMatch']='0x67041002';entry['TemperatureFanControl']=False
        with self.assertRaises(ValueError):module.cursor_profile(plistlib.dumps(self.info))


if __name__=='__main__':unittest.main()
