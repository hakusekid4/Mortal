"""規則のボットの応答部と、手元対局の要約(計画の継ぎ目)の試験。

確かめるのは外から見える振る舞いだけ:
- どの局面でも、選べる手の中から返す
- RiichiLab の request_action を受けて、request_id 付きの MJAI の 1 手を返す
- 手元で半荘を打たせた要約に、チョンボ・終わった局・応答時間が出る
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from riichienv import ActionType, GameRule, RiichiEnv, calculate_shanten  # noqa: E402

import local_match  # noqa: E402
import rule_bot  # noqa: E402

WIN = {ActionType.TSUMO, ActionType.RON}


def play_some_turns(limit=400):
    """規則のボット 4 体で打ち、(局面, 選んだ手) を順に返す。"""
    env = RiichiEnv(game_mode="4p-red-half", rule=GameRule.default_tenhou())
    obs_dict = env.reset()
    bot = rule_bot.RuleBot()
    seen = 0
    while not env.done() and seen < limit:
        actions = {}
        for pid, obs in obs_dict.items():
            a = bot.choose(obs)
            actions[pid] = a
            yield obs, a
            seen += 1
        obs_dict = env.step(actions)


def key(a):
    return (a.action_type, a.tile, tuple(a.consume_tiles))


class 規則のボット(unittest.TestCase):
    def test_いつも選べる手の中から返す(self):
        n = 0
        for obs, a in play_some_turns():
            self.assertIn(key(a), {key(x) for x in obs.legal_actions()})
            n += 1
        self.assertGreater(n, 50)

    def test_和了できるときは和了する(self):
        for obs, a in play_some_turns(2000):
            if any(x.action_type in WIN for x in obs.legal_actions()):
                self.assertIn(a.action_type, WIN)

    def test_立直できるときは立直する(self):
        for obs, a in play_some_turns(2000):
            types = {x.action_type for x in obs.legal_actions()}
            if ActionType.RIICHI in types and not types & WIN:
                self.assertEqual(a.action_type, ActionType.RIICHI)

    def test_捨て牌は向聴数が最も小さくなるものを選ぶ(self):
        checked = 0
        for obs, a in play_some_turns(600):
            legal = obs.legal_actions()
            if a.action_type != ActionType.DISCARD:
                continue
            hand = list(obs.hand)

            def after(tile):
                rest = list(hand)
                rest.remove(tile)
                return calculate_shanten(rest)

            best = min(after(x.tile) for x in legal if x.action_type == ActionType.DISCARD)
            self.assertEqual(after(a.tile), best)
            checked += 1
        self.assertGreater(checked, 10)


class RiichiLabの手番の通知に答える(unittest.TestCase):
    def test_request_idを付けてMJAIの1手を返す(self):
        env = RiichiEnv(game_mode="4p-red-half", rule=GameRule.default_tenhou())
        obs = env.reset()[0]
        msg = {"type": "request_action", "request_id": 42,
               "observation": obs.serialize_to_base64(), "unknown_field": 1}
        out = rule_bot.respond(rule_bot.RuleBot(), msg)
        self.assertEqual(out["request_id"], 42)
        legal = [x.to_mjai() for x in obs.legal_actions()]
        legal = [json.loads(x) if isinstance(x, str) else x for x in legal]
        self.assertIn({k: v for k, v in out.items() if k != "request_id"}, legal)


class 手元対局の要約(unittest.TestCase):
    def test_半荘を打たせると要約が出る(self):
        s = local_match.run(bot="rule", games=1, seed=1)
        self.assertEqual(s["games"], 1)
        self.assertEqual(s["finished"], 1)
        self.assertEqual(s["chombo"], 0)
        self.assertLess(s["max_response_ms"], 3000)
        self.assertGreater(s["actions"], 0)

    def test_jsonで出せる(self):
        rc = local_match.main(["--bot", "rule", "--games", "1", "--json", "--seed", "2"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
