"""Regression checks for Leopard's kernel vtable acceptance rules."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from leopard_kext_abi import compare


class VTableTests(unittest.TestCase):
    def test_legacy_single_destructor_and_local_override(self):
        parent = dict(entries=[('BaseD0Ev',True),('_RESERVEDBase0',True)])
        child = dict(terminated=True,entries=[('ChildD0Ev',True),('_RESERVEDBase0',False),('extra',True)])
        self.assertEqual(compare(child,parent),[])

    def test_double_destructor_shifts_reserved_slot(self):
        parent = dict(entries=[('BaseD0Ev',True),('release',True),('_RESERVEDBase0',True)])
        child = dict(terminated=True,entries=[('ChildD1Ev',True),('ChildD0Ev',True),('release',False),('_RESERVEDBase0',False)])
        errors = compare(child,parent)
        self.assertTrue(any('slot 2' in e for e in errors))
        self.assertTrue(any('single D0' in e for e in errors))

    def test_missing_terminator(self):
        self.assertTrue(compare(dict(terminated=False,entries=[]),dict(entries=[])))

    def test_short_table(self):
        self.assertTrue(compare(dict(terminated=True,entries=[]),dict(entries=[('method',True)])))


if __name__ == '__main__':
    unittest.main()
