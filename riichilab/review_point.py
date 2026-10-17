"""見直し点の判定(2027-01-31)。hakuseki-zero がランク戦 50 局以上・40 位以内にいるか。

    python riichilab/review_point.py --dry-run --json

通らなければ、やり方の見直し(天鳳の運営への問い合わせの再検討を含む)を本人に出す。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from weekly_summary import fetch_board, find_bot  # noqa: E402

MIN_GAMES = 50
MAX_RANK = 40


def judge(bot_name: str = "hakuseki-zero", fetch=fetch_board) -> dict:
    row = find_bot(bot_name, fetch)
    games = int(row.get("total_games", 0)) if row else 0
    rank = row.get("current_rank") if row else None
    ok = bool(row) and games >= MIN_GAMES and rank is not None and rank <= MAX_RANK
    return {"bot_name": bot_name, "games": games, "rank": rank,
            "rating": row.get("rating") if row else None,
            "need": {"games": MIN_GAMES, "rank": MAX_RANK}, "pass": ok}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="見直し点の判定")
    ap.add_argument("--bot-name", default="hakuseki-zero")
    ap.add_argument("--dry-run", action="store_true", help="判定だけして、終了コードは常に 0")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = judge(a.bot_name)
    print(json.dumps(r, ensure_ascii=False) if a.json else
          f"{r['bot_name']}: {r['games']} 局・{r['rank']} 位 → {'通過' if r['pass'] else '見直し'}")
    return 0 if (a.dry_run or r["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
