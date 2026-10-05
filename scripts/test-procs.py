#!/usr/bin/env python3
"""Process memory regression tests for the Python sampler."""

from pathlib import Path
import os
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = {"__name__": "sampler_test", "__file__": str(ROOT / "sampler.py")}
exec(compile((ROOT / "sampler.py").read_bytes(), "sampler.py", "exec"), NAMESPACE)

ROLLUP = """\
55d0c000-7ffd0000 ---p 00000000 00:00 0    [rollup]
Rss:              468120 kB
Pss:              343208 kB
Pss_Anon:         300000 kB
"""


class ProcessMemoryTests(unittest.TestCase):
    def test_pss_is_read_from_the_rollup_in_bytes(self):
        self.assertEqual(NAMESPACE["parse_pss"](ROLLUP), 343208 * 1024)
        self.assertIsNone(NAMESPACE["parse_pss"]("Rss: 12 kB\n"))

    def test_pss_is_reported_only_when_asked(self):
        sampler = NAMESPACE["ProcessSampler"]()
        plain = sampler.sample(1.0, full=True)
        self.assertNotIn("pss", plain)
        self.assertNotIn("pss", plain["all"][0])
        with_pss = sampler.sample(1.0, full=True, pss=True)
        self.assertTrue(with_pss["pss"])
        mine = next(g for g in with_pss["all"] if g["pssCount"] > 0)
        self.assertGreater(mine["pss"], 0)

    def test_pss_is_reused_between_refreshes(self):
        sampler = NAMESPACE["ProcessSampler"]()
        sampler.sample(1.0, pss=True)
        with patch.dict(NAMESPACE, read_pss=lambda pid: self.fail("read again")):
            sampler.sample(1.0, pss=True)
        self.assertIn(os.getpid(), sampler.pss)

    def test_unreadable_processes_fall_back_to_rss(self):
        sampler = NAMESPACE["ProcessSampler"]()
        with patch.dict(NAMESPACE, read_pss=lambda pid: None):
            sample = sampler.sample(1.0, full=True, pss=True)
        for group in sample["all"]:
            self.assertEqual(group["pssCount"], 0)
            self.assertEqual(group["pss"], group["mem"])


if __name__ == "__main__":
    unittest.main()
