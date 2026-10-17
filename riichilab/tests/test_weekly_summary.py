"""週の要約の試験。夜の回し役の記録と順位表から、週次まとめに貼る 1 節を作る。"""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import weekly_summary as ws  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))
BOARD = [
    {"bot_name": "someone", "current_rank": 1, "rating": 2084, "total_games": 261, "rating_1w_delta": -3},
    {"bot_name": "hakuseki-zero", "current_rank": 57, "rating": 1702, "total_games": 12,
     "rating_1w_delta": 40},
]


def fetch_pages(limit, offset):
    return BOARD[offset:offset + limit]


def game(day, rank, chombo=0, timeouts=0, ended=True, bot="zero"):
    return {"type": "game", "at": f"{day}T02:30:00+09:00", "bot": bot, "rank": rank,
            "chombo": chombo, "timeouts": timeouts, "ended": ended}


class 週の要約(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rec = Path(self.tmp.name) / "records"
        self.rec.mkdir()

    def write(self, day, rows):
        with (self.rec / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def test_週の対局と順位表をまとめる(self):
        self.write("2026-10-12", [game("2026-10-12", 4), game("2026-10-12", 2)])
        self.write("2026-10-13", [game("2026-10-13", 1, timeouts=1), game("2026-10-13", 4, chombo=1)])
        self.write("2026-10-05", [game("2026-10-05", 1)])  # 前の週は数えない
        s = ws.summarize(self.rec, week="2026-W42", bot_name="hakuseki-zero", fetch=fetch_pages)
        self.assertEqual(s["games"], 4)
        self.assertEqual(s["rank_counts"], {"1": 1, "2": 1, "3": 0, "4": 2})
        self.assertAlmostEqual(s["avg_rank"], 2.75)
        self.assertEqual(s["chombo"], 1)
        self.assertEqual(s["timeouts"], 1)
        self.assertEqual(len(s["lost_games"]), 2)  # 4 着の局
        self.assertEqual(s["board"]["current_rank"], 57)
        self.assertEqual(s["board"]["rating"], 1702)

    def test_対局が無い週はそう出す(self):
        s = ws.summarize(self.rec, week="2026-W42", bot_name="hakuseki-zero", fetch=fetch_pages)
        self.assertEqual(s["games"], 0)
        self.assertIn("今週は対局なし", ws.to_markdown(s))

    def test_順位表に居なくても落ちない(self):
        s = ws.summarize(self.rec, week="2026-W42", bot_name="not-registered", fetch=fetch_pages)
        self.assertIsNone(s["board"])
        self.assertIn("順位表に無い", ws.to_markdown(s))

    def test_改良の方向の欄がある(self):
        self.write("2026-10-12", [game("2026-10-12", 3)])
        md = ws.to_markdown(ws.summarize(self.rec, week="2026-W42", bot_name="hakuseki-zero",
                                         fetch=fetch_pages))
        self.assertIn("改良の方向", md)
        self.assertIn("57 位", md)

    def test_ファイルに書き出す(self):
        out = Path(self.tmp.name) / "reports"
        rc = ws.main(["--records", str(self.rec), "--week", "2026-W42", "--bot-name", "hakuseki-zero",
                      "--out-dir", str(out), "--offline"])
        self.assertEqual(rc, 0)
        self.assertTrue((out / "2026-W42.md").exists())
        self.assertTrue((out / "2026-W42.json").exists())


if __name__ == "__main__":
    unittest.main()
