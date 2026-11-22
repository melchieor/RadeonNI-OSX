"""Actual artifact writer preserves RGBA bytes and flips PPM rows correctly."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class Images(unittest.TestCase):
 def test_exact_raw_and_viewable_orientation(self):
  s=(ROOT/'tools/guest/pixel-render-probe.c').read_text();i=s.index('static int ppm(');body=s[i:s.index('\n}',i)+2]
  prefix='#include <stdio.h>\n#include <stdint.h>\nstatic const char *output;\n'
  main='int main(int argc,char **argv){(void)argc;output=argv[1];unsigned char p[]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16};return !ppm("gold",p,2,2);}\n'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(prefix+body+main)
   subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test'),d],check=True)
   self.assertEqual((p/'gold.rgba').read_bytes(),bytes(range(1,17)))
   self.assertEqual((p/'gold.ppm').read_bytes(),b'P6\n2 2\n255\n'+bytes([9,10,11,13,14,15,1,2,3,5,6,7]))
if __name__=='__main__':unittest.main()
