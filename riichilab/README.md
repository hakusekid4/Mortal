# riichilab

[RiichiLab](https://riichi.dev) (an open arena for Riichi Mahjong AI) bot built on top of Mortal.
The ranked bot is **hakuseki-zero**, trained only by self-play in riichienv (no Tenhou logs).

- Code: AGPL-3.0-or-later, same as Mortal.
- Weights and bot tokens are **not** in this repository.

## Secret guard

Run before committing (or install it as a pre-commit hook):

    python riichilab/secret_guard.py --repo .
    python riichilab/secret_guard.py --install-hook

It fails on tracked `.env` files, weight files (`.pth`, `.pt`, `.ckpt`, `.safetensors`, `.onnx`)
and token-like strings, printing only file and line, never the value.

## Rule bot (hakuseki-rule)

A tiny rule-based bot used only to pass RiichiLab validation: win > riichi > discard that minimizes shanten > never call.
Local check (the plan's seam): 4 rule bots play N hanchan in riichienv and report chombo / finished / max response time.

    pip install riichienv
    python riichilab/local_match.py --bot rule --games 10 --json

## Tests

    python -m unittest discover -s riichilab/tests
