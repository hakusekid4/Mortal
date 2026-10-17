"""token_check の試験。中身を出さず、ある・無いだけを答える。"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import token_check as tc  # noqa: E402


class トークンの確認(unittest.TestCase):
    def test_あれば0_無ければ1_中身は出さない(self):
        with tempfile.TemporaryDirectory() as d:
            secret = "abc" + "defgh12345"
            (Path(d) / "hakuseki-rule.token").write_text(secret, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tc.main(["--names", "hakuseki-rule", "--dir", d]), 0)
                self.assertEqual(tc.main(["--names", "hakuseki-rule,hakuseki-zero", "--dir", d]), 1)
            self.assertNotIn(secret, out.getvalue())


if __name__ == "__main__":
    unittest.main()
