"""公開リポジトリにトークン・.env・重みを入れないための検査。

git に載っている(コミット済み・コミット予定の)ファイルだけを見る。手元にあるだけの
ファイルは見ない。見つけたら、どのファイルの何行目かだけを出し、中身は出さない。

    python riichilab/secret_guard.py --repo .          # 終了コード 0 = 問題なし / 1 = 止める
    python riichilab/secret_guard.py --install-hook    # コミット前に自動で走らせる
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# 重み・学習済みモデルの拡張子。公開リポジトリには置かない(ADR 0004)
WEIGHT_SUFFIXES = {".pth", ".pt", ".ckpt", ".safetensors", ".onnx"}

# トークンらしい文字列。読み込む書き方(環境変数・f 文字列・見本の文字列)は引っかけない
TOKEN_PATTERNS = [
    re.compile(r"""\b\w*(?:TOKEN|SECRET|API_KEY)\w*\s*[:=]\s*["'][A-Za-z0-9_\-]{24,}["']""", re.I),
    re.compile(r"""Bearer [A-Za-z0-9._\-]{24,}"""),
    re.compile(r"""\bgh[pousr]_[A-Za-z0-9]{30,}"""),
]


def tracked_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "--cached"],
                         check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def scan(repo: Path) -> list[str]:
    """問題の一覧を返す。空なら問題なし。"""
    repo = Path(repo)
    found: list[str] = []
    for name in tracked_files(repo):
        p = Path(name)
        if p.name == ".env" or p.name.startswith(".env."):
            found.append(f"{name}: .env ファイル")
            continue
        if p.suffix.lower() in WEIGHT_SUFFIXES:
            found.append(f"{name}: 重みのファイル")
            continue
        path = repo / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if any(pat.search(line) for pat in TOKEN_PATTERNS):
                found.append(f"{name}:{i}: トークンらしい文字列")
    return found


HOOK = """#!/bin/sh
python "$(git rev-parse --show-toplevel)/riichilab/secret_guard.py" --repo "$(git rev-parse --show-toplevel)"
"""


def install_hook(repo: Path) -> Path:
    hooks = Path(subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "hooks"],
                                check=True, capture_output=True, text=True).stdout.strip())
    if not hooks.is_absolute():
        hooks = repo / hooks
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text(HOOK, encoding="utf-8")
    hook.chmod(0o755)
    return hook


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--install-hook", action="store_true")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    if a.install_hook:
        print(f"入れた: {install_hook(repo)}")
        return 0
    found = scan(repo)
    for f in found:
        print(f"止める: {f}")
    if not found:
        print("問題なし")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
