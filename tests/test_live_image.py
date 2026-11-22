"""Verify chunked storage, stale plans, read/write failures and dirty retention."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class LiveImageTest(unittest.TestCase):
 def test_image_and_failure_paths(self):
  with tempfile.TemporaryDirectory() as d:
   binary=Path(d)/'live-image'
   subprocess.run(['clang','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
    '-I'+str(ROOT/'hw'),str(ROOT/'tests/live_image.c'),str(ROOT/'hw/rdn_live_image.c'),'-o',str(binary)],check=True)
   subprocess.run([str(binary)],check=True)
if __name__=='__main__':unittest.main()
