"""記録の確かめ役の試験。チケット 05 の完了条件(検証が通った・ランク戦を N 回最後まで打った)を記録だけから判定する。

- 検証: ws_client の要約(type summary)で validation_passed が真のものが 1 行あれば通過
- ランク戦: 夜の回し役の 1 局(type game)か、ws_client のランク戦の要約で、最後まで打ちチョンボ 0 のものを数える
- 記録が無い・壊れた行は数えない(落ちない)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_record  # noqa: E402


class 記録の確かめ役(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rec = Path(self.tmp.name)

    def put(self, name, rows):
        with (self.rec / name).open("a", encoding="utf-8") as f:
            for r in rows:
                f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")

    def run_main(self, *args):
        return check_record.main(["--record-dir", str(self.rec), *args])

    def test_記録が無ければ通らない(self):
        self.assertEqual(self.run_main("--validated"), 1)
        self.assertEqual(self.run_main("--ranked-games", "1"), 1)

    def test_検証が通った要約があれば通る(self):
        self.put("validate.jsonl", [{"type": "summary", "validation_passed": True, "ended": True}])
        self.assertEqual(self.run_main("--validated"), 0)

    def test_検証に落ちた要約だけなら通らない(self):
        self.put("validate.jsonl", [{"type": "summary", "validation_passed": False, "ended": True}])
        self.assertEqual(self.run_main("--validated"), 1)

    def test_ランク戦は最後まで打ちチョンボ0の局だけ数える(self):
        self.put("2026-10-30.jsonl", [
            {"type": "game", "ended": True, "chombo": 0},
            {"type": "game", "ended": False, "chombo": 0},
            {"type": "game", "ended": True, "chombo": 1},
            {"type": "night", "games": 3},
        ])
        self.put("ranked.jsonl", [{"type": "summary", "validation_passed": None, "ended": True, "chombo": 0}])
        self.assertEqual(check_record.count(self.rec)["ranked_games"], 2)
        self.assertEqual(self.run_main("--ranked-games", "2"), 0)
        self.assertEqual(self.run_main("--ranked-games", "3"), 1)

    def test_検証の要約はランク戦に数えない(self):
        self.put("validate.jsonl", [{"type": "summary", "validation_passed": True, "ended": True, "chombo": 0}])
        self.assertEqual(self.run_main("--ranked-games", "1"), 1)

    def test_壊れた行は飛ばす(self):
        self.put("x.jsonl", ["{壊れた", "", '"文字列だけ"',
                             json.dumps({"type": "summary", "validation_passed": True})])
        self.assertEqual(self.run_main("--validated"), 0)

    def test_両方の条件を同時に見る(self):
        self.put("validate.jsonl", [{"type": "summary", "validation_passed": True}])
        self.assertEqual(self.run_main("--validated", "--ranked-games", "1"), 1)
        self.put("ranked.jsonl", [{"type": "summary", "validation_passed": None, "ended": True, "chombo": 0}])
        self.assertEqual(self.run_main("--validated", "--ranked-games", "1"), 0)


if __name__ == "__main__":
    unittest.main()
