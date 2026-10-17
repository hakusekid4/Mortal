"""夜の回し役の試験。1 局ぶんの対局は差し替えて、止まり方だけを確かめる。

- 時間の中で半荘を続けて打ち、1 局ごとに 1 行記録する
- チョンボが 1 回出たら、その晩を止める
- 時間切れ・切断では止めない
- ボットの指定が空なら打たない(hakuseki-zero の重みができるまで)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nightly  # noqa: E402


class Clock:
    def __init__(self, step):
        self.t = 0.0
        self.step = step

    def __call__(self):
        return self.t

    def tick(self):
        self.t += self.step


def game(chombo=0, timeouts=0, ended=True):
    return {"ended": ended, "chombo": chombo, "timeouts": timeouts, "requests": 100,
            "seat": 0, "end": {"scores": [30000, 25000, 25000, 20000]}}


def runner(results, clock):
    it = iter(results)

    def play():
        clock.tick()
        return next(it)
    return play


class 夜の回し役(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rec = Path(self.tmp.name)

    def rows(self):
        out = []
        for f in sorted(self.rec.glob("*.jsonl")):
            out += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]
        return out

    def test_時間いっぱい打って1局ごとに記録する(self):
        clock = Clock(step=40 * 60)  # 1 局 40 分
        s = nightly.run_night(runner([game()] * 10, clock), hours=3, record_dir=self.rec, now=clock)
        self.assertEqual(s["stopped"], "time")
        self.assertEqual(s["games"], 5)  # 0,40,80,120,160 分に始めた 5 局
        games = [r for r in self.rows() if r["type"] == "game"]
        self.assertEqual(len(games), 5)
        self.assertEqual(games[0]["rank"], 1)

    def test_チョンボが1回出たらその晩を止める(self):
        clock = Clock(step=60)
        s = nightly.run_night(runner([game(), game(chombo=1), game()], clock),
                              hours=3, record_dir=self.rec, now=clock)
        self.assertEqual(s["stopped"], "chombo")
        self.assertEqual(s["games"], 2)
        self.assertEqual(s["chombo"], 1)

    def test_時間切れと切断では止めない(self):
        clock = Clock(step=60 * 60)
        s = nightly.run_night(runner([game(timeouts=2), game(ended=False), game()], clock),
                              hours=3, record_dir=self.rec, now=clock)
        self.assertEqual(s["stopped"], "time")
        self.assertEqual(s["games"], 3)
        self.assertEqual(s["timeouts"], 2)
        self.assertEqual(s["disconnects"], 1)

    def test_3回続けてつながらなければその晩をあきらめる(self):
        clock = Clock(step=60)

        def play():
            clock.tick()
            raise ConnectionRefusedError()
        s = nightly.run_night(play, hours=3, record_dir=self.rec, now=clock)
        self.assertEqual(s["stopped"], "errors")
        self.assertEqual(s["games"], 3)
        self.assertEqual(s["disconnects"], 3)

    def test_ボットの指定が空なら打たない(self):
        rc = nightly.main(["--bot", "", "--hours", "3", "--record-dir", str(self.rec)])
        self.assertEqual(rc, 0)
        self.assertEqual([r for r in self.rows() if r["type"] == "game"], [])


if __name__ == "__main__":
    unittest.main()
