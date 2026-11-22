"""Test the real allocator-to-snapshot plan with sanitizers."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class LivePlanTest(unittest.TestCase):
 def test_ranges_and_incomplete_layouts(self):
  with tempfile.TemporaryDirectory() as d:
   binary=Path(d)/'live-plan'
   subprocess.run(['clang','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
    '-I'+str(ROOT/'hw'),str(ROOT/'tests/live_plan.c'),str(ROOT/'hw/rdn_live_plan.c'),
    str(ROOT/'hw/rdn_snapshot_plan.c'),str(ROOT/'hw/rdn_mem.c'),'-o',str(binary)],check=True)
   subprocess.run([str(binary)],check=True)
if __name__=='__main__':unittest.main()
