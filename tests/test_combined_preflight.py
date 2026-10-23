"""Offline structural smoke tests for the combined preflight; no ROM download."""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from combined_preflight import permitted, parse_partitions

LPSAMPLE="""Slot 0:
Metadata version: 10.2
Partition table:
------------------------
  Name: system_a
  Group: main_a
  Attributes: readonly
  Extents:
    0 .. 1023 linear super 2048
------------------------
  Name: system_b
  Group: main_b
  Attributes: readonly
  Extents:
    0 .. 99 linear super 4096
------------------------
  Name: vendor_b
  Group: main_b
  Attributes: readonly
  Extents:
------------------------
Super partition layout:
------------------------
super: 2048 .. 3072: system_a (1024 sectors)
Block device table:
------------------------
  Partition name: super
"""

class CombinedPreflightTests(unittest.TestCase):
    def test_exact_33_allowlisted_files(self):
        entries=permitted()
        self.assertEqual(len(entries),33)
        self.assertEqual(len(set(entries)),33)
        self.assertTrue(all(x.endswith('.apk') for x in entries))
        self.assertTrue(all(x.split(':')[0] in {'product_a','system_a','system_ext_a'} for x in entries))
        self.assertEqual(sum(x.startswith('product_a:') for x in entries),23)
        self.assertEqual(sum(x.startswith('system_a:') for x in entries),9)
        self.assertEqual(sum(x.startswith('system_ext_a:') for x in entries),1)
    def test_lp_contains_a_and_small_b_but_not_empty(self):
        names=parse_partitions(LPSAMPLE,0)
        self.assertEqual(names,[(0,'system_a'),(0,'system_b')])
    def test_lp_refuses_missing_sections(self):
        with self.assertRaises(RuntimeError):
            parse_partitions('Name: system_a',0)

if __name__=='__main__':
    unittest.main()
