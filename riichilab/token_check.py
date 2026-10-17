"""ボットのトークンが母艦に置けたかを、中身を出さずに確かめる。

    python riichilab/token_check.py --names hakuseki-rule,hakuseki-zero

置き場は ~/.riichilab/<ボット名>.token(リポジトリの外)。ある・無いだけを答える。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DIR = Path.home() / ".riichilab"


def check(names: list[str], base: Path = DIR) -> dict[str, bool]:
    out = {}
    for n in names:
        p = base / f"{n}.token"
        out[n] = p.is_file() and len(p.read_text(encoding="utf-8").strip()) >= 8
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", required=True)
    ap.add_argument("--dir", type=Path, default=DIR)
    a = ap.parse_args(argv)
    res = check([n.strip() for n in a.names.split(",") if n.strip()], a.dir)
    for n, ok in res.items():
        print(f"{n}: {'ある' if ok else '無い'}")
    return 0 if all(res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
