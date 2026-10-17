"""secret_guard の試験。公開リポジトリにトークン・.env・重みを入れないための検査。

ADR 0004(ai-config): コードは公開、重みとトークンは公開しない。公開は取り消せないので、
コミットの前に機械で止める。
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import secret_guard as sg  # noqa: E402

FAKE = "9f8e7d6c5b4a" + "39281706f5e4d3c2b1a0"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


class 秘密の検査(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        (self.repo / "bot.py").write_text("print('hello')\n", encoding="utf-8")
        git(self.repo, "add", "bot.py")

    def _add(self, name, text="x"):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        git(self.repo, "add", name)

    def test_何も混ぜていなければ通る(self):
        self.assertEqual(sg.scan(self.repo), [])
        self.assertEqual(sg.main(["--repo", str(self.repo)]), 0)

    def test_重みのファイルは止まる(self):
        for name in ("weights/mortal.pth", "a.pt", "b.ckpt", "c.safetensors", "d.onnx"):
            with self.subTest(name=name):
                self._add(name)
                self.assertTrue(any(name in f for f in sg.scan(self.repo)))
        self.assertEqual(sg.main(["--repo", str(self.repo)]), 1)

    def test_envファイルは止まる(self):
        self._add(".env", "RIICHILAB_TOKEN=abc\n")
        self.assertTrue(any(".env" in f for f in sg.scan(self.repo)))

    def test_トークンらしい文字列は止まる(self):
        # 偽のトークンは分割して組み立てる(この試験ファイル自体が検査に引っかからないように)
        cases = [
            'TOKEN = "rl_' + FAKE + '"\n',
            'headers = {"Authorization": "Bear' + 'er ' + FAKE + '"}\n',
            "gh = 'gh" + "p_" + FAKE + "ABCD'\n",
        ]
        for i, text in enumerate(cases):
            with self.subTest(text=text):
                self._add(f"leak{i}.py", text)
                self.assertTrue(any(f"leak{i}.py" in f for f in sg.scan(self.repo)))

    def test_トークンを読む書き方は止めない(self):
        ok = (
            'TOKEN = os.environ["RIICHILAB_TOKEN"]\n'
            'HEADERS = {"Authorization": f"Bearer {token}"}\n'
            'TOKEN = "your-bot-token-here"\n'
        )
        self._add("client.py", ok)
        self.assertEqual(sg.scan(self.repo), [])

    def test_出力にトークンの中身を出さない(self):
        secret = "rl_" + FAKE
        self._add("leak.py", f'TOKEN = "{secret}"\n')
        self.assertFalse(any(secret in f for f in sg.scan(self.repo)))

    def test_コミット前の印に載っていない手元のファイルは見ない(self):
        (self.repo / "local.pth").write_text("x", encoding="utf-8")
        self.assertEqual(sg.scan(self.repo), [])


if __name__ == "__main__":
    unittest.main()
