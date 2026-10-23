"""Offline unit tests: no firmware download or super.img modification."""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from erofs_trial import proposed, exclusions, compare_trees, is_removed

class ErofsTrialTests(unittest.TestCase):
    def test_proposal_is_24_and_keeps_nine(self):
        trial,reviewed=proposed()
        self.assertEqual(len(trial),24)
        self.assertEqual(len(reviewed),33)
        self.assertEqual(len(set(reviewed)-set(trial)),9)
        self.assertEqual(len(exclusions("product_a",trial)),18)
        self.assertEqual(len(exclusions("system_a",trial)),6)
        self.assertEqual(len(exclusions("system_ext_a",trial)),0)
    def test_exclusion_is_recursive_but_not_prefix(self):
        folders=["/app/YouTube"]
        self.assertTrue(is_removed("/app/YouTube",folders))
        self.assertTrue(is_removed("/app/YouTube/oat/arm64/base.odex",folders))
        self.assertFalse(is_removed("/app/YouTubeKids/Keep.apk",folders))
        self.assertFalse(is_removed("/app/YouTube2",folders))
    def test_retained_records_must_be_identical(self):
        before={"/": {"mode":493}, "/app/YouTube": {"mode":493},
                "/app/YouTube/YouTube.apk":{"sha256":"original"},
                "/app/Keep":{"sha256":"retained"}}
        after={"/":{"mode":493},"/app/Keep":{"sha256":"retained"}}
        c=compare_trees(before,after,["/app/YouTube"])
        self.assertTrue(c["passed"])
        self.assertEqual(c["source_entries_excluded"],2)
        after["/app/Keep"]["sha256"]="different"
        c=compare_trees(before,after,["/app/YouTube"])
        self.assertFalse(c["passed"])
        self.assertEqual(len(c["different_retained"]),1)
    def test_unexpected_files_are_blocking(self):
        before={"/":{"mode":493}}
        after={"/":{"mode":493},"/extra.apk":{"sha256":"a"}}
        self.assertFalse(compare_trees(before,after,[])["passed"])

if __name__=="__main__":
    unittest.main()
