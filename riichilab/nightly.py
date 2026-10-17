"""夜の回し役。決めた時間の中で、ランク戦の半荘を続けて打つ。

- 1 局ごとに 1 行、記録(JSON Lines)を日本時間の日付のファイルへ足す
- チョンボが 1 回出たら、その晩を止める(続けるほどレートが落ちる。不具合を直してから)
- 時間切れ・切断では止めない(罰が無い)。件数だけ数える
- ボットの指定が空なら打たない(hakuseki-zero の重みができるまで)

    python riichilab/nightly.py --bot rule --hours 3 --token-file ~/.riichilab/hakuseki-rule.token
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

JST = dt.timezone(dt.timedelta(hours=9))
RECORD_DIR = Path.home() / ".riichilab" / "records"


def _rank(game: dict) -> int | None:
    end = game.get("end") or {}
    scores, seat = end.get("scores") or game.get("scores"), game.get("seat")
    if not isinstance(scores, list) or seat is None or seat >= len(scores):
        return None
    mine = scores[seat]
    # 同点は席の早い方を上にする(天鳳と同じ)
    return 1 + sum(1 for i, x in enumerate(scores) if x > mine or (x == mine and i < seat))


def _append(record_dir: Path, row: dict) -> None:
    record_dir.mkdir(parents=True, exist_ok=True)
    day = dt.datetime.now(JST).strftime("%Y-%m-%d")
    with (record_dir / f"{day}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_night(play, hours: float, record_dir: Path, now=time.time, bot: str = "") -> dict:
    """play() は半荘 1 回を打ち、ws_client.play と同じ形の要約を返す。"""
    until = now() + hours * 3600
    s = {"bot": bot, "games": 0, "chombo": 0, "timeouts": 0, "disconnects": 0, "stopped": "time"}
    errors_in_row = 0
    while now() < until:
        try:
            g = play()
            errors_in_row = 0
        except Exception as e:  # つながらない・途中で切れた。罰は無いので数えて続ける
            errors_in_row += 1
            g = {"ended": False, "error": type(e).__name__}
        s["games"] += 1
        s["chombo"] += g.get("chombo", 0)
        s["timeouts"] += g.get("timeouts", 0)
        if not g.get("ended"):
            s["disconnects"] += 1
        _append(record_dir, {
            "type": "game", "at": dt.datetime.now(JST).isoformat(timespec="seconds"), "bot": bot,
            "rank": _rank(g), "seat": g.get("seat"), "scores": g.get("scores"), "end": g.get("end"), "ended": g.get("ended"),
            "chombo": g.get("chombo", 0), "timeouts": g.get("timeouts", 0),
            "requests": g.get("requests", 0), "error": g.get("error")})
        if g.get("chombo", 0) > 0:
            s["stopped"] = "chombo"
            break
        if errors_in_row >= 3:  # 3 回続けてつながらなければ、その晩はあきらめる
            s["stopped"] = "errors"
            break
    _append(record_dir, {"type": "night", "at": dt.datetime.now(JST).isoformat(timespec="seconds"), **s})
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="夜の回し役")
    ap.add_argument("--bot", default="", help="空なら打たない")
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--token-file", type=Path)
    ap.add_argument("--record-dir", type=Path, default=RECORD_DIR)
    a = ap.parse_args(argv)
    if not a.bot:
        _append(a.record_dir, {"type": "night", "at": dt.datetime.now(JST).isoformat(timespec="seconds"),
                               "bot": "", "games": 0, "stopped": "no_bot"})
        print("ボットの指定が空なので打たない")
        return 0
    import ws_client
    token = ws_client.read_token(a.token_file)
    bot_cls = ws_client.BOTS[a.bot]

    def play():
        return asyncio.run(ws_client.play(ws_client.ENDPOINTS["ranked"], token, bot_cls()))

    s = run_night(play, a.hours, a.record_dir, bot=a.bot)
    print(json.dumps(s, ensure_ascii=False))
    return 1 if s["stopped"] == "chombo" else 0


if __name__ == "__main__":
    sys.exit(main())
