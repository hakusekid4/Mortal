"""つなぎ役の試験。手元で立てる偽の RiichiLab を相手にする(本番にはつながない)。

確かめること:
- 検証の流れ(start_game → 手番の通知 → end_game → validation_result)を最後まで打てる
- 手番の通知には request_id 付きで、選べる手の中から答える
- 知らない種類のメッセージや欄で落ちない
- action_ack の rejected をチョンボ、defaulted を時間切れとして数える
- トークンを記録にも画面にも出さない
"""
import asyncio
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from riichienv import GameRule, RiichiEnv  # noqa: E402
from websockets.asyncio.server import serve  # noqa: E402

import rule_bot  # noqa: E402
import ws_client  # noqa: E402

TOKEN = "fake-" + "token-for-tests-only"


class FakeRiichiLab:
    """検証対局と同じ順でメッセージを送る偽のサーバー。受け取った答えを控える。"""

    def __init__(self, turns=5, ack_status=("accepted",), validation=True):
        self.turns = turns
        self.ack_status = ack_status
        self.validation = validation
        self.replies = []
        self.legal = []
        self.auth = None

    async def handler(self, ws):
        self.auth = ws.request.headers.get("Authorization")
        if self.auth != f"Bearer {TOKEN}":
            await ws.close(code=4001, reason="Token verification failed")
            return
        env = RiichiEnv(game_mode="4p-red-half", rule=GameRule.default_tenhou(), seed=3)
        obs = env.reset()[0]
        await ws.send(json.dumps({"type": "start_game", "id": 0}))
        await ws.send(json.dumps({"type": "something_new", "x": 1}))
        for i in range(self.turns):
            legal = [json.loads(a.to_mjai()) for a in obs.legal_actions()]
            self.legal.append(legal)
            await ws.send(json.dumps({
                "type": "request_action", "request_id": i, "new_field": True,
                "time": {"grace_ms": 3000, "bank_ms": 15000, "deadline_ms": 18000},
                "possible_actions": legal, "observation": obs.serialize_to_base64()}))
            reply = json.loads(await ws.recv())
            self.replies.append(reply)
            status = self.ack_status[i % len(self.ack_status)]
            await ws.send(json.dumps({"type": "action_ack", "request_id": i, "status": status,
                                      "elapsed_ms": 5, "bank_consumed_ms": 0, "bank_ms": 15000}))
        await ws.send(json.dumps({"type": "end_game"}))
        if self.validation:
            await ws.send(json.dumps({"type": "validation_result", "passed": True}))
        await ws.close()


def run_against(fake, **kw):
    async def go():
        async with serve(fake.handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            return await ws_client.play(f"ws://127.0.0.1:{port}/ws/validate", TOKEN,
                                        rule_bot.RuleBot(), **kw)
    return asyncio.run(go())


class つなぎ役(unittest.TestCase):
    def test_検証の流れを最後まで打てる(self):
        fake = FakeRiichiLab(turns=5)
        s = run_against(fake)
        self.assertTrue(s["ended"])
        self.assertTrue(s["validation_passed"])
        self.assertEqual(s["requests"], 5)
        self.assertEqual(s["chombo"], 0)

    def test_request_id付きで選べる手の中から答える(self):
        fake = FakeRiichiLab(turns=4)
        run_against(fake)
        for i, (reply, legal) in enumerate(zip(fake.replies, fake.legal)):
            self.assertEqual(reply["request_id"], i)
            self.assertIn({k: v for k, v in reply.items() if k != "request_id"}, legal)

    def test_トークンをAuthorizationで送る(self):
        fake = FakeRiichiLab(turns=1)
        run_against(fake)
        self.assertEqual(fake.auth, f"Bearer {TOKEN}")

    def test_rejectedはチョンボ_defaultedは時間切れと数える(self):
        fake = FakeRiichiLab(turns=4, ack_status=("accepted", "rejected", "defaulted", "accepted"))
        s = run_against(fake)
        self.assertEqual(s["chombo"], 1)
        self.assertEqual(s["timeouts"], 1)

    def test_トークンを記録にも画面にも出さない(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "game.jsonl"
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                run_against(FakeRiichiLab(turns=3), record=log)
            self.assertTrue(log.exists())
            self.assertNotIn(TOKEN, log.read_text(encoding="utf-8"))
            self.assertNotIn(TOKEN, out.getvalue())

    def test_トークンはファイルか環境変数から読む(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "hakuseki-rule.token"
            f.write_text(TOKEN + "\n", encoding="utf-8")
            self.assertEqual(ws_client.read_token(token_file=f, env={}), TOKEN)
        self.assertEqual(ws_client.read_token(token_file=None, env={"RIICHILAB_TOKEN": TOKEN}), TOKEN)
        with self.assertRaises(SystemExit):
            ws_client.read_token(token_file=None, env={})


if __name__ == "__main__":
    unittest.main()
