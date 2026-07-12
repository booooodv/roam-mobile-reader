import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class BuildTest(unittest.TestCase):
    def test_example_build_is_private_data_free(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=json.loads((ROOT/'config.example.json').read_text())
            cfg['chapters'][0]['path']=str(ROOT/'examples/notes/chapter-1')
            cp=Path(d)/'config.json'; cp.write_text(json.dumps(cfg))
            out=Path(d)/'out'
            subprocess.run([sys.executable,str(ROOT/'build.py'),'--config',str(cp),'--output',str(out)],check=True)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual(len(manifest),1)
            self.assertEqual(manifest[0]['title'],'01 Example lesson')
            page=(out/'content/c1-01.html').read_text()
            self.assertIn('First nested child',page)
            blob=(out/'manifest.json').read_text()+page
            for marker in ('/Users/finn','concept_test','日进斗斗金','192.168.1.'):
                self.assertNotIn(marker,blob)

if __name__=='__main__': unittest.main()
