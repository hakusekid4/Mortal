"""手元対局の要約(計画の継ぎ目)。

riichienv で同じボット 4 体に半荘を N 回打たせ、次を 1 つの JSON にまとめる。
- chombo: 選べる手の外を返した回数(RiichiLab ならチョンボ)
- finished: 最後まで終わった半荘の数
- max_response_ms: 1 手にかかった最長の時間(RiichiLab の猶予は 1 手 3 秒)

    python riichilab/local_match.py --bot rule --games 10 --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from riichienv import GameRule, RiichiEnv  # noqa: E402

import rule_bot  # noqa: E402

BOTS = {"rule": rule_bot.RuleBot}
MAX_STEPS = 20000  # 半荘 1 回でこれを超えたら、終わらなかったと数える


def _key(a):
    return (a.action_type, a.tile, tuple(a.consume_tiles))


def run(bot: str = "rule", games: int = 10, seed: int = 0) -> dict:
    make = BOTS[bot]
    s = {"bot": bot, "games": games, "finished": 0, "chombo": 0,
         "actions": 0, "max_response_ms": 0.0, "ranks": []}
    for g in range(games):
        env = RiichiEnv(game_mode="4p-red-half", rule=GameRule.default_tenhou(), seed=seed + g)
        obs_dict = env.reset()
        bots = {pid: make() for pid in range(4)}
        steps = 0
        while not env.done() and steps < MAX_STEPS:
            actions = {}
            for pid, obs in obs_dict.items():
                t0 = time.perf_counter()
                a = bots[pid].choose(obs)
                ms = (time.perf_counter() - t0) * 1000
                s["max_response_ms"] = max(s["max_response_ms"], ms)
                s["actions"] += 1
                if _key(a) not in {_key(x) for x in obs.legal_actions()}:
                    s["chombo"] += 1
                actions[pid] = a
            obs_dict = env.step(actions)
            steps += 1
        if env.done():
            s["finished"] += 1
            s["ranks"].append(list(env.ranks()))
    s["max_response_ms"] = round(s["max_response_ms"], 1)
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="手元対局の要約")
    ap.add_argument("--bot", default="rule", choices=sorted(BOTS))
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = run(a.bot, a.games, a.seed)
    if a.json:
        print(json.dumps(s, ensure_ascii=False))
    else:
        print(f"{s['bot']}: 半荘 {s['finished']}/{s['games']} 終了、チョンボ {s['chombo']}、"
              f"最長 {s['max_response_ms']} ms、{s['actions']} 手")
    ok = s["chombo"] == 0 and s["finished"] == s["games"] and s["max_response_ms"] < 3000
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
