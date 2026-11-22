"""Run production marker reporter with missing and inaccessible path results."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class MarkerStatus(unittest.TestCase):
 def test_access_error_is_not_absence(self):
  s=(ROOT/'tools/guest/leopard-qe-status.c').read_text();a=s.index('static void marker_status(');body=s[a:s.index('\n}',a)+2]
  code='''#include <stdio.h>
#include <errno.h>
#include <string.h>
#define F_OK 0
static int failure;
static int access(const char *p,int mode){(void)p;(void)mode;errno=failure;return failure?-1:0;}
'''+body+'''\nint main(void){marker_status("test","p");failure=ENOENT;marker_status("test","p");failure=EACCES;marker_status("test","p");failure=ENOTDIR;marker_status("test","p");}\n'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(code);subprocess.run(['cc',str(p/'test.c'),'-o',str(p/'test')],check=True)
   lines=subprocess.check_output([str(p/'test')],text=True).splitlines()
   self.assertEqual(lines[:2],['test opt-out marker=present','test opt-out marker=absent'])
   self.assertIn('access-error',lines[2]);self.assertIn('access-error',lines[3])
if __name__=='__main__':unittest.main()
