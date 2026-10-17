"""規則のボット(hakuseki-rule)の応答部。

RiichiLab の検証対局を通し、つなぎ方を確かめるためだけのボット。強さは問わない。
規則: 和了 > 立直 > 向聴数(あと何枚で和了か)を最も減らす捨て牌 > 鳴かない。
返す手は必ず「選べる手」(legal_actions)の中から選ぶ。外れた手を返すとチョンボになる。
"""
from __future__ import annotations

import json

from riichienv import ActionType, Observation, calculate_shanten

WIN = (ActionType.TSUMO, ActionType.RON)


class RuleBot:
    name = "hakuseki-rule"

    def choose(self, obs):
        legal = list(obs.legal_actions())
        if not legal:
            raise ValueError("選べる手が無い")
        by_type: dict = {}
        for a in legal:
            by_type.setdefault(a.action_type, []).append(a)
        for t in WIN:
            if t in by_type:
                return by_type[t][0]
        if ActionType.RIICHI in by_type:
            return by_type[ActionType.RIICHI][0]
        discards = by_type.get(ActionType.DISCARD)
        if discards:
            hand = list(obs.hand)

            def after(a):
                rest = list(hand)
                rest.remove(a.tile)
                return calculate_shanten(rest)

            # 同じ向聴数なら、手牌の並びで後ろ(字牌・端寄り)を先に切る
            return min(discards, key=lambda a: (after(a), -a.tile))
        if ActionType.PASS in by_type:
            return by_type[ActionType.PASS][0]
        return legal[0]


def to_mjai(action) -> dict:
    m = action.to_mjai()
    return json.loads(m) if isinstance(m, str) else dict(m)


def respond(bot, msg: dict) -> dict:
    """RiichiLab の request_action に、request_id 付きの MJAI の 1 手で答える。知らない欄は無視する。"""
    obs = Observation.deserialize_from_base64(msg["observation"])
    out = to_mjai(bot.choose(obs))
    if "request_id" in msg:
        out["request_id"] = msg["request_id"]
    return out
