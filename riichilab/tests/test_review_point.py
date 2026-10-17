"""見直し点(2027-01-31)の判定の試験。ランク戦 50 局以上・40 位以内なら通る。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import review_point as rp  # noqa: E402


def board(rank, games):
    def fetch(limit, offset):
        rows = [{"bot_name": "hakuseki-zero", "current_rank": rank, "total_games": games, "rating": 1900}]
        return rows if offset == 0 else []
    return fetch


class 見直し点(unittest.TestCase):
    def test_50局以上かつ40位以内なら通る(self):
        self.assertTrue(rp.judge("hakuseki-zero", fetch=board(40, 50))["pass"])

    def test_局数が足りなければ通らない(self):
        r = rp.judge("hakuseki-zero", fetch=board(10, 49))
        self.assertFalse(r["pass"])
        self.assertEqual(r["games"], 49)

    def test_41位以下なら通らない(self):
        self.assertFalse(rp.judge("hakuseki-zero", fetch=board(41, 300))["pass"])

    def test_順位表に居なければ通らない(self):
        r = rp.judge("hakuseki-zero", fetch=lambda limit, offset: [])
        self.assertEqual((r["games"], r["rank"], r["pass"]), (0, None, False))


if __name__ == "__main__":
    unittest.main()
