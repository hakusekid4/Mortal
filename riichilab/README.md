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

## Connecting to RiichiLab

The token stays outside the repository (`~/.riichilab/<bot>.token` or `RIICHILAB_TOKEN`). It is never printed or recorded.

    pip install websockets
    python riichilab/ws_client.py --mode validate --bot rule --token-file ~/.riichilab/hakuseki-rule.token

Only `request_action` is answered (with `request_id`); unknown messages are ignored. `action_ack` statuses are counted: `rejected` = chombo, `defaulted` = timeout.

## Nightly ranked play

`.github/workflows/riichilab-nightly.yml` runs every night 02:00–05:00 JST on a self-hosted runner.
The bot is chosen by the repository variable `RIICHILAB_NIGHTLY_BOT` (empty = do not play) and the token file by `RIICHILAB_NIGHTLY_TOKEN_NAME`.
One chombo stops the night; timeouts and disconnects are only counted. Records go to `~/.riichilab/records/<date>.jsonl`.

## Weekly summary

`.github/workflows/riichilab-weekly.yml` writes `riichilab/reports/weekly/<ISO week>.md` every Sunday 19:00 JST from the night records and the public leaderboard (`api.riichi.dev`).

## Tests

    python -m unittest discover -s riichilab/tests
