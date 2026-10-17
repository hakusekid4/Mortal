"""つなぎ役。WebSocket で RiichiLab につなぎ、半荘 1 回を最後まで打つ。

- 手番の通知(request_action)にだけ答える。request_id を付けて返す
- 知らない種類のメッセージや欄は無視する(サーバーは予告なく増やすことがある)
- action_ack の rejected はチョンボ、defaulted は時間切れとして数える
- トークンは環境変数 RIICHILAB_TOKEN か、リポジトリの外のファイルから読む。記録にも画面にも出さない

    python riichilab/ws_client.py --mode validate --bot rule --token-file ~/.riichilab/hakuseki-rule.token
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from websockets.asyncio.client import connect  # noqa: E402

import rule_bot  # noqa: E402

ENDPOINTS = {
    "validate": "wss://game.riichi.dev/ws/validate",
    "ranked": "wss://game.riichi.dev/ws/ranked",
}
BOTS = {"rule": rule_bot.RuleBot}


def read_token(token_file: Path | None = None, env: dict | None = None) -> str:
    env = os.environ if env is None else env
    if token_file:
        tok = Path(token_file).expanduser().read_text(encoding="utf-8").strip()
        if tok:
            return tok
    tok = (env.get("RIICHILAB_TOKEN") or "").strip()
    if tok:
        return tok
    raise SystemExit("トークンが無い: --token-file か環境変数 RIICHILAB_TOKEN で渡す")


def _write(record: Path | None, row: dict) -> None:
    if record is None:
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    with record.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


async def play(url: str, token: str, bot, record: Path | None = None) -> dict:
    """半荘 1 回(検証なら東風戦 1 回)を打ち、要約を返す。"""
    s = {"ended": False, "validation_passed": None, "requests": 0, "chombo": 0,
         "timeouts": 0, "seat": None, "max_response_ms": 0.0, "end": None}
    record = Path(record) if record else None
    async with connect(url, additional_headers={"Authorization": f"Bearer {token}"},
                       max_size=None) as ws:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (TypeError, ValueError):
                continue
            t = msg.get("type")
            if t == "start_game":
                s["seat"] = msg.get("id")
            elif t == "request_action":
                t0 = time.perf_counter()
                reply = rule_bot.respond(bot, msg)
                s["max_response_ms"] = max(s["max_response_ms"], (time.perf_counter() - t0) * 1000)
                s["requests"] += 1
                await ws.send(json.dumps(reply))
            elif t == "action_ack":
                status = msg.get("status")
                if status == "rejected":
                    s["chombo"] += 1
                elif status == "defaulted":
                    s["timeouts"] += 1
                if status != "accepted":
                    _write(record, {"type": "ack", "request_id": msg.get("request_id"),
                                    "status": status, "reason": msg.get("reason")})
            elif t == "end_game":
                s["ended"] = True
                s["end"] = {k: v for k, v in msg.items() if k != "type"}
            elif t == "validation_result":
                s["validation_passed"] = bool(msg.get("passed"))
                if not s["validation_passed"]:
                    s["validation_reason"] = msg.get("reason")
            elif t == "hora" or t == "ryukyoku":
                _write(record, {"type": t, **{k: msg.get(k) for k in ("actor", "target", "deltas", "scores")}})
            # それ以外(知らない種類を含む)は無視する
    s["max_response_ms"] = round(s["max_response_ms"], 1)
    _write(record, {"type": "summary", **s})
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RiichiLab につないで 1 回打つ")
    ap.add_argument("--mode", choices=sorted(ENDPOINTS), required=True)
    ap.add_argument("--bot", choices=sorted(BOTS), default="rule")
    ap.add_argument("--token-file", type=Path)
    ap.add_argument("--record", type=Path, help="1 行 1 件の記録(JSON Lines)の置き場")
    ap.add_argument("--url", help="試験用に入口を差し替える")
    a = ap.parse_args(argv)
    token = read_token(a.token_file)
    s = asyncio.run(play(a.url or ENDPOINTS[a.mode], token, BOTS[a.bot](), a.record))
    print(json.dumps(s, ensure_ascii=False))
    if a.mode == "validate":
        return 0 if s["validation_passed"] else 1
    return 0 if s["ended"] and s["chombo"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
