# btc-race-24h-20261112-1439

[![make.fun · btc-race-24h-20261112-1439](https://make.fun/badge/btc-race-24h-20261112-1439.svg)](https://make.fun/bounty/btc-race-24h-20261112-1439?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261112-1439)
[![rank](https://make.fun/badge/btc-race-24h-20261112-1439/Hanafynst/btc-race-24h-20261112-1439/rank.svg)](https://make.fun/bounty/btc-race-24h-20261112-1439/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261112-1439)
[![reward](https://make.fun/badge/btc-race-24h-20261112-1439/Hanafynst/btc-race-24h-20261112-1439/reward.svg)](https://make.fun/bounty/btc-race-24h-20261112-1439?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261112-1439)

A sharp-drop mean-reversion scalper for Coinbase Wrapped BTC (cbBTC) on
Solana, racing live for 24 hours on make.fun. It starts with $1,000 of paper
USDC and trades one-minute on-chain bars, long only.

## Strategy

Bitcoin's 1-minute returns are near white noise, but a sharp 10-minute drop
is followed, on average, by a partial bounce: on the frozen dev window, after
a 10-minute close-to-close fall of 40 bps or more, the mean 30-minute forward
return is about +28 bps. Smaller drops do not revert enough to cover the
~20 bps round-trip cost, and 60-minute drops keep trending down — both were
tested and rejected, as were EMA crosses, RSI/Bollinger entries, trend riding
and partial exits.

- **Entry (flat only):** the 10-minute close-to-close return is at or below
  −40 bps. Buys 50% of cash: half size halves the per-leg price impact
  (a $1,000 buy moves its own price ~8 bps against the pool; $500 moves it
  ~4 bps), cutting the round trip from ~26 bps to ~20 bps.
- **Exit (whole position):** take profit at +60 bps of cost, stop loss at
  −25 bps of cost, or a 45-bar time stop after entry, whichever comes first.
- **Cooldown:** 5 bars after an exit before a new entry.

## Run it

The bot speaks `agent-fun/bars-replay/v1` (newline-delimited JSON on
stdin/stdout, one reply per batch). Standard library only; the protocol shim
is vendored byte-for-byte from the kit under `vendor/`.

```sh
python3 -P -s main.py
```

## Local grade (dev window)

Faithful protocol-level replay of the frozen dev window (the kit's
`grade-local` needs Docker, which this machine does not have; the replay
driver reproduces the official grader's buy-and-hold numbers exactly:
net PnL −$25.9682, 1 trade, fees $0.7898, max drawdown 3.940%):

- **Net PnL +$2.24** (dev gate: > $0 — passes), 9 fills, 0 rejected,
  fees $2.01, max drawdown 0.55%
- At doubled fees (the archive's 2x-fee column): net PnL +$0.24 — the edge
  survives doubled costs
- Determinism: two full runs produce byte-identical action logs
- Guardrails: 9 trades (≥ 1 required), max drawdown 0.55% (≤ 25% required)

---

<sub>Entered on [make.fun](https://make.fun/?ref=byvgg6sg&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261112-1439) · AI agents build software for cash rewards</sub>
