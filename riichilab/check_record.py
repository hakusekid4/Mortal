"""記録の確かめ役。チケット 05 の完了条件を、母艦の記録(JSON Lines)だけから判定する。

- --validated: ws_client の要約(type summary)で validation_passed が真のものが 1 行以上
- --ranked-games N: 最後まで打ちチョンボ 0 のランク戦が N 回以上
  (夜の回し役の type game と、ws_client --mode ranked の要約の両方を数える)
- 壊れた行は飛ばす。条件をすべて満たせば終了コード 0、どれか欠ければ 1

    python riichilab/check_record.py --validated --ranked-games 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RECORD_DIR = Path.home() / ".riichilab" / "records"


def _rows(record_dir: Path):
    for f in sorted(Path(record_dir).expanduser().glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield row


def count(record_dir: Path) -> dict:
    c = {"validated": 0, "ranked_games": 0}
    for r in _rows(record_dir):
        t = r.get("type")
        if t == "summary" and r.get("validation_passed") is True:
            c["validated"] += 1
        elif t in ("game", "summary") and r.get("validation_passed") is None \
                and r.get("ended") is True and r.get("chombo", 0) == 0:
            c["ranked_games"] += 1
    return c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="記録から検証とランク戦の回数を確かめる")
    ap.add_argument("--validated", action="store_true", help="検証の通過を求める")
    ap.add_argument("--ranked-games", type=int, default=0, help="最後まで打ったランク戦の最低回数")
    ap.add_argument("--record-dir", type=Path, default=RECORD_DIR)
    a = ap.parse_args(argv)
    c = count(a.record_dir)
    ok = (not a.validated or c["validated"] > 0) and c["ranked_games"] >= a.ranked_games
    print(json.dumps({**c, "ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
