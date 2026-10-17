"""週の要約。夜の回し役の記録と RiichiLab の順位表から、週次まとめに貼る 1 節を作る。

    python riichilab/weekly_summary.py --bot-name hakuseki-zero --out-dir riichilab/reports/weekly

週は ISO 週(月曜はじまり、日本時間)。出すもの: 順位・レート・局数・着順の内訳・
負けた局(4 着)・チョンボと時間切れと切断の件数。改良の方向を本人が書き込む欄も置く。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

JST = dt.timezone(dt.timedelta(hours=9))
API = "https://api.riichi.dev/api/v1/leaderboard?limit={limit}&offset={offset}"
RECORD_DIR = Path.home() / ".riichilab" / "records"


def fetch_board(limit: int, offset: int) -> list[dict]:
    with urllib.request.urlopen(API.format(limit=limit, offset=offset), timeout=20) as r:
        return json.load(r).get("data") or []


def find_bot(name: str, fetch=fetch_board, limit: int = 50) -> dict | None:
    offset = 0
    while True:
        page = fetch(limit, offset)
        for row in page:
            if row.get("bot_name") == name:
                return row
        if len(page) < limit:
            return None
        offset += limit


def week_days(week: str) -> list[dt.date]:
    y, w = week.split("-W")
    monday = dt.date.fromisocalendar(int(y), int(w), 1)
    return [monday + dt.timedelta(days=i) for i in range(7)]


def this_week() -> str:
    y, w, _ = dt.datetime.now(JST).date().isocalendar()
    return f"{y}-W{w:02d}"


def summarize(records: Path, week: str, bot_name: str, fetch=fetch_board) -> dict:
    games = []
    for day in week_days(week):
        f = Path(records) / f"{day.isoformat()}.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "game":
                games.append(row)
    ranks = [g["rank"] for g in games if g.get("rank")]
    s = {
        "week": week, "bot_name": bot_name, "games": len(games),
        "rank_counts": {str(k): ranks.count(k) for k in (1, 2, 3, 4)},
        "avg_rank": round(sum(ranks) / len(ranks), 3) if ranks else None,
        "chombo": sum(g.get("chombo", 0) for g in games),
        "timeouts": sum(g.get("timeouts", 0) for g in games),
        "disconnects": sum(1 for g in games if not g.get("ended")),
        "lost_games": [g.get("at") for g in games if g.get("rank") == 4],
    }
    try:
        s["board"] = find_bot(bot_name, fetch) if fetch else None
    except OSError as e:
        s["board"], s["board_error"] = None, type(e).__name__
    return s


def to_markdown(s: dict) -> str:
    lines = [f"### RiichiLab の麻雀ボット({s['bot_name']}、{s['week']})", ""]
    b = s.get("board")
    if b:
        d = b.get("rating_1w_delta")
        lines.append(f"- 順位表: {b['current_rank']} 位、レート {b['rating']}"
                     f"(先週から {d:+d})、通算 {b['total_games']} 局" if isinstance(d, int) else
                     f"- 順位表: {b['current_rank']} 位、レート {b['rating']}、通算 {b['total_games']} 局")
    else:
        lines.append("- 順位表: 順位表に無い(まだ 1 局も打っていないか、止めている)")
    if s["games"] == 0:
        lines.append("- 今週は対局なし")
    else:
        rc = s["rank_counts"]
        lines.append(f"- 今週 {s['games']} 局。着順 1 着 {rc['1']} / 2 着 {rc['2']} / 3 着 {rc['3']} / "
                     f"4 着 {rc['4']}、平均 {s['avg_rank']}")
        lines.append(f"- チョンボ {s['chombo']} 回、時間切れ {s['timeouts']} 回、切断 {s['disconnects']} 回")
        if s["lost_games"]:
            lines.append(f"- 負けた局(4 着): {', '.join(x or '?' for x in s['lost_games'][:10])}")
    lines += ["", "改良の方向(本人が決める。決めたら理由と一緒に 1 行):", "- "]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="週の要約")
    ap.add_argument("--records", type=Path, default=RECORD_DIR)
    ap.add_argument("--week", default=None, help="例 2026-W42。省くと今週")
    ap.add_argument("--bot-name", default="hakuseki-zero")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--offline", action="store_true", help="順位表を取りに行かない")
    a = ap.parse_args(argv)
    week = a.week or this_week()
    s = summarize(a.records, week, a.bot_name, fetch=None if a.offline else fetch_board)
    md = to_markdown(s)
    if a.out_dir:
        a.out_dir.mkdir(parents=True, exist_ok=True)
        (a.out_dir / f"{week}.md").write_text(md, encoding="utf-8")
        (a.out_dir / f"{week}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
